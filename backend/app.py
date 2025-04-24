import datetime
from flask import Flask, request, jsonify
import psycopg2
import chat
import awss3
import urllib.parse
from flask_cors import CORS
from elevenlabs.client import ElevenLabs
from elevenlabs import play
import os
import uuid
from dotenv import load_dotenv
from knowledge_base import add_transcript
import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

load_dotenv()

# Initialize ElevenLabs for Voice Responses
client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

@app.route("/")
def home():
    return 'We are live 🚀'


def connect_to_db():
    try:
        connection = psycopg2.connect(
            dbname="test",
            user="test",
            password="test",
            host="localhost",
            port="5432"
        )
        print("DB connection successful")
        return connection
    except Exception as e:
        print(f"DB connection failed: {e}")
        return None

store =[]
@app.route("/ask", methods=["POST"])
def ask_question():
    try:
        data = request.json
        question = data.get("question", "")
        if not question:
            return jsonify({"error": "No question asked"})
        
        response = chat.graph.invoke({"question": ", ".join(store)+ " " + question})
        answer = response["answer"]
        store.append(f"question: {question}, response: {answer}")
        # Convert the answer to speech
        # audio = client.text_to_speech.convert_as_stream(
        #     text=answer,
        #     voice_id="onwK4e9ZLuTAKqWW03F9",
        #     model_id="eleven_multilingual_v2",
        #     output_format="mp3_44100_128",
        # )
        
        return jsonify({"answer": response["answer"]})
        
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/loginInfo', methods=['POST'])
def get_login_information():
    connection = connect_to_db()

    if connection is None:
        return {"error": "Database connection failed"}, 500

    try:
        login_data = request.json
        email = login_data.get('email')
        password = login_data.get('password')
        username = login_data.get('username')
        user_role = login_data.get('user_role')

        cursor = connection.cursor()


        cursor.execute(
            "SELECT * FROM public.users WHERE email = %s AND password = %s",
            (email, password)
        )
        user = cursor.fetchone()
        cursor.close()
        if user:
            return jsonify({
                'status': 'success',
                'message': f'Login successful for {email}',
                'email': email,
                'user_role': user[3]
            })
        else:
            return jsonify({
                'status': 'failure',
                'message': 'Invalid email or password'
            }), 401

    except Exception as e:
        print("Error during login:", e)
        return {"error": str(e)}, 500

    finally:
        connection.close()



@app.route('/signupInfo', methods=['POST'])
def get_signup_information():
    connection = connect_to_db()

    if connection is None:
        return {"error": "Database connection failed"}, 500
    
    try:
        signup = request.json
        email = signup.get('email')
        username = signup.get('username')
        password = signup.get('password')
        user_role = signup.get('user_role')

        cursor = connection.cursor()

        # Assuming you have a `users` table with columns `email`, `username`, `password`
        cursor.execute(
            "INSERT INTO public.users (email, username, password, user_role) VALUES (%s, %s, %s,%s)",
            (email, username, password, user_role)
        )

        connection.commit()
        cursor.close()

        return jsonify({
            'status': 'success',
            'message': f'Signup info received for {email} and username {username}'
        })
        
    except Exception as e:
        print("Error inserting signup data:", e)
        return {"error": str(e)}, 500

    finally:
        connection.close()

import logging
logging.basicConfig(level=logging.DEBUG)
@app.route('/uploadTranscripts', methods=['POST'] )
def upload_file():
    if 'file' not in request.files:
        return {"error": "No file part"}, 400

    file = request.files['file']
    filename = file.filename
    my_uuid = uuid.uuid4()
    safe_filename = urllib.parse.quote(filename)
    mimetype = file.mimetype
    
    #Save file temoporarily
    temp_path = f"tmp/{my_uuid}_{safe_filename}"
    file.save(temp_path)
    
    #save to vector store
    try:
        add_transcript(temp_path)
    except Exception as e:
        return {"error": f"Failed to add transcript to vector store: {e}"}, 500
    
    #file url 
    file_url = awss3.s3.uploadToS3(file, f"uploads/{my_uuid}", mimetype)
    print(file_url)

    # Connect to the database
    connection = connect_to_db()
    if connection is None:
        return {"error": "Database connection failed"}, 500

    try:
        cursor = connection.cursor()
        # Insert the file URL into the transcripts table
        cursor.execute("INSERT INTO public.transcripts (file_url) VALUES (%s)", (file_url,))
        connection.commit()
        cursor.close()
    except Exception as e:
        #logging.error(f"Error inserting into database: {e}")
        return {"error": f"error inserting {safe_filename} into database"}, 500
    finally:
        connection.close()
    return {'url': file_url}, 201


@app.route('/retrieveTranscripts', methods=['GET'])
def send_user_transcripts():
    try:
        # Connect to the database
        connection = connect_to_db()
        cursor = connection.cursor()

        # Query the database for all file URLs
        cursor.execute("SELECT file_url FROM transcripts")
        urls = cursor.fetchall()

        # Close the database connection
        cursor.close()
        connection.close()

        # Extract URLs from the query result
        url_list = [url[0] for url in urls]

        # Return the URLs in a JSON response
        return jsonify({'success': True, 'transcripts': url_list}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    

@app.route('/adminRetrieveDataSource', methods=['GET'])
def retrieve_admin_files():
    try:
        # Connect to DB
        connection = connect_to_db()
        cursor = connection.cursor()

        # Fetch all entries from adminFile
        select_sql = """
        SELECT id, urlfile, name, size, uploadedOn, created_at
        FROM adminFile
        ORDER BY created_at DESC;
        """
        cursor.execute(select_sql)
        rows = cursor.fetchall()

        # Format the data
        files = [
            {
                "id": row[0],
                "url": row[1],
                "name": row[2],
                "size": row[3],
                "uploadedOn": row[4],
                "created_at": row[5].isoformat() if row[5] else None
            }
            for row in rows
        ]

        return jsonify(files), 200

    except Exception as e:
        logging.error(f"Error retrieving data sources: {e}")
        return {"error": "Could not retrieve data sources"}, 500

    finally:
        if connection:
            connection.close()


@app.route('/adminupload', methods=['POST'])
def upload_adminfile():
    connection = connect_to_db()
    file = request.files['mydatasource']
    print(file.filename)
    print('this is the file', file)
    if 'mydatasource' not in request.files:
        return {"error": "No file part in the request"}, 400
    
    if file.filename == '':
        return {"error": "No selected file"}, 400

    try:
        # Generate safe identifiers
        filename = file.filename
        safe_filename = urllib.parse.quote(filename)
        mimetype = file.mimetype
        file_size = len(file.read())  # read to get size
        file.seek(0)  # reset after read
        uploaded_on = datetime.datetime.utcnow().isoformat()
        my_uuid = uuid.uuid4()

        # Upload to AWS S3
        file_url = awss3.s3.uploadToS3(file, f"uploads/{my_uuid}", mimetype)
        print(file_url)

        # Connect to DB
        
        cursor = connection.cursor()

        # Ensure table exists
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS adminFile (
            id SERIAL PRIMARY KEY,
            urlfile TEXT NOT NULL,
            name TEXT NOT NULL,
            size TEXT NOT NULL,
            uploadedOn TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_sql)

        # Insert into table
        insert_sql = """
        INSERT INTO adminFile (urlfile, name, size, uploadedOn)
        VALUES (%s, %s, %s, %s);
        """
        cursor.execute(insert_sql, (file_url, filename, str(file_size), uploaded_on))
        connection.commit()

        return {"success": True, "url": file_url, 
                'uploadedFiles': [{
                    'name': filename,
                    'size':str(file_size),
                    'uploadedOn': uploaded_on
                }]}, 201

    except Exception as e:
        logging.error(f"Error inserting {safe_filename} into database: {e}")
        return {"error": f"Server error while uploading {safe_filename}"}, 500

    finally:
        if connection:
            connection.close()
            
if __name__ == "__main__":
    app.run(debug=True)
    try:
        _, audio = ask_question()
        play(audio)
    except Exception as e:
        print(f"Error occurred: {str(e)}")