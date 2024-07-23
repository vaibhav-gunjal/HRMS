import fitz

def generate_internship_letter(recipient_name, company_name, reporting_p,joining_date):
    text = f"""
    
                                                                                                <b>Date: {joining_date}</b>
 
Dear <b>{recipient_name}</b>,

<b>{company_name}</b> is pleased to offer you an internship 
opportunity as a Python Developer Intern. You will report directly to <b>{reporting_p} </b>
This position is located in Pune, Maharashtra. 

As you will be receiving academic credit for this position, you will be paid Stipend according 
to your performance. Additionally, students do not receive benefits as part of their 
internship program.

Your schedule will be approximately 8hrs per day.Your assignment will start from 
<b>{joining_date}</b>.

Please review, sign and return via to confirm acceptance. 
Absolute Global Outsourcing Pvt.Ltd. is keen that there is a secure environment for client
and internally too.

Congratulations and welcome to the team! 

Regards, 
<b>Nikhil Sathe</b> 
Director of Operations 
Absolute Global Outsourcing Pvt Ltd.

    """
    return text

def text_slicing(text):
    date=text.split('\n')[2]

    text1=text.split('\n')[4]

    first_paragraph=text.split('\n')[6:9]
    first_paragraph = ' '.join(first_paragraph)

    second_paragraph = text.split('\n')[10:13]
    second_paragraph =' '.join(second_paragraph)

    third_paragraph = text.split('\n')[14:16]
    third_paragraph=' '.join(third_paragraph)

    fourth_paragraph = text.split('\n')[17:20]
    fourth_paragraph =' '.join(fourth_paragraph)

    congrats = text.split('\n')[21]
    

    rega = text.split('\n')[23]

    nikhil = text.split('\n')[24]
    

    director = text.split('\n')[25]
    

    com_name = text.split('\n')[26]
    
    return date,text1,first_paragraph,second_paragraph,third_paragraph,fourth_paragraph,congrats,rega,nikhil,director,com_name

def insert_heading(pdf_file_path):
    heading = "<span style='text-decoration: underline; font-weight: bold;'>Internship Offer Letter</span>"
    rect = fitz.Rect(215, 100,500,300)
    doc = fitz.Document(pdf_file_path)
    page = doc[0]
    page.insert_htmlbox(rect, heading, css="* {font-family: sans-serif;font-size:22px ;}")
    doc.save('new_abs.pdf')


def insert_text(date,text1,first_paragraph,second_paragraph,third_paragraph,fourth_paragraph,congrats,rega,nikhil,director,com_name):
    # add position of letter
    rect = fitz.Rect(420, 150,580,300)
    doc = fitz.Document('new_abs.pdf')
    page = doc[0]
    page.insert_htmlbox(rect, date, css="* {font-family: sans-serif;font-size:14px ;}")

    # add position of rcepiants name
    rect = fitz.Rect(70, 200,580,300)
    page = doc[0]
    page.insert_htmlbox(rect, text1, css="* {font-family: sans-serif;font-size:14px ;}")

    # add position of first para 
    rect = fitz.Rect(70, 225,580,300)
    page = doc[0]
    page.insert_htmlbox(rect, first_paragraph, css="* {font-family: sans-serif;font-size:14px ;}")

    # add position of second paragraph
    rect = fitz.Rect(70,290,580,400)
    page = doc[0]
    page.insert_htmlbox(rect, second_paragraph, css="* {font-family: sans-serif;font-size:14px ;}")

    # add position of third paragraph
    rect = fitz.Rect(70,355,580,400)
    page = doc[0]
    page.insert_htmlbox(rect, third_paragraph, css="* {font-family: sans-serif;font-size:14px ;}")

    # add position of fourth paragraph
    rect = fitz.Rect(70,395,580,500)
    page = doc[0]
    page.insert_htmlbox(rect, fourth_paragraph, css="* {font-family: sans-serif;font-size:14px ;}")

    # add position of congrats paragraph
    rect = fitz.Rect(70,450,580,500)
    page = doc[0]
    page.insert_htmlbox(rect, congrats, css="* {font-family: sans-serif;font-size:14px ;}")

    # position og regards
    rect = fitz.Rect(70,500,580,600)
    page = doc[0]
    page.insert_htmlbox(rect, rega, css="* {font-family: sans-serif;font-size:14px ;}")

    # position of name and company
    rect = fitz.Rect(70,600,300,700)
    page = doc[0]
    page.insert_htmlbox(rect, nikhil, css="* {font-family: sans-serif;font-size:14px ;}")

    rect = fitz.Rect(70,620,300,700)
    page.insert_htmlbox(rect, director, css="* {font-family: sans-serif;font-size:14px ;}")

    rect = fitz.Rect(70,635,300,700)
    page.insert_htmlbox(rect, com_name, css="* {font-family: sans-serif;font-size:14px ;}")


    doc.save('final_offer_letter.pdf')


def main(recipient_name, company_name, reporting_p, joining_date):
    # Generate the internship offer letter text
    letter_text = generate_internship_letter(recipient_name, company_name, reporting_p, joining_date)
    
    # Slice the text into components
    date, text1, first_paragraph, second_paragraph, third_paragraph, fourth_paragraph, congrats, rega, nikhil, director, com_name = text_slicing(letter_text)
    
    # Insert the heading into the PDF
    insert_heading('abs_globe.pdf')
    
    # Insert the text into the PDF
    insert_text(date, text1, first_paragraph, second_paragraph, third_paragraph, fourth_paragraph, congrats, rega, nikhil, director, com_name)

# Example usage:
main("John Doe", "XYZ Corporation", "Jane Smith", "2024-05-01")

