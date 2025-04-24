from langchain_core.documents import Document
from morgan_course_data.api import MorganCourseData
from vector_store import vector_store

# Initialize the MorganCourseData with the desired term
morgan_data = MorganCourseData(term="SPRING_2025")

# Fetch COSC courses
cosc_courses = morgan_data.get_courses_by_subject_abbreviation("COSC")

# Create documents for each course
course_documents = []

for course in cosc_courses:
    instructor_names = set()  # Use a set to avoid duplicate instructor names
    sections_info = []
    for section in course.sections:
        instructor_names.add(section.instructor)
        section_meetings = []
        for meeting in section.meetings:
            section_meetings.append({
                "days": meeting['days'],
                "start_time": meeting['start_time'],
                "end_time": meeting['end_time'],
                "building": meeting['building'],
            })
        sections_info.append({
            "instructor": section.instructor,
            "type": section.type,
            "meetings": section_meetings,
        })

    instructor_list = list(instructor_names)  # Convert the set to a list

    page_content = f"Name: {course.name}\n" \
                   f"Abbreviation: {course.subject_abbreviation}\n" \
                   f"Description: {course.description}\n" \
                   f"Number: {course.number}\n" \
                   f"Prerequisites: {course.prerequisites}\n" \
                   f"Instructors: {', '.join(instructor_list)}\n" \
                   f"Sections: {sections_info}"

    metadata = {
        "course_name": course.full_name,
        "description": course.description,
        "prerequisites": course.prerequisites,
        "instructors": instructor_list,
        "sections": sections_info,
    }

    document = Document(page_content=page_content, metadata=metadata)
    course_documents.append(document)

# Add course documents to the vector store
vector_store.add_documents(documents=course_documents)