from morgan_course_data.api import MorganCourseData
import re
import json
morgan_data = MorganCourseData(term="FALL_2025")

cosc_courses = morgan_data.get_courses_by_subject_abbreviation("COSC")

sections_data = []

for course in cosc_courses:
    course_sections = []
    for section in course.sections:
        # Convert CourseSection object to a dictionary
        section_dict = {
            "title": section.title,
            "section": section.section,
            "type": section.type,
            "crn": section.crn,
            "instructional_method": section.instructional_method,
            "instructor": section.instructor,
            "enrollment_available": section.enrollment_available,
            "meetings": section.meetings,
        }
        course_sections.append(section_dict)
    sections_data.append(course_sections)

# Now sections_data is a list of lists of dictionaries, which you can work with like JSON
# For example, to print it as a JSON string:
print(json.dumps(sections_data, indent=2))

