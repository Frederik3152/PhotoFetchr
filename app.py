# Import libraries
from flask import Flask, render_template, request, Response, jsonify
import psycopg2
from PIL import Image
from io import BytesIO
from datetime import date

app = Flask(__name__, static_folder='static')

# Database configuration
db_config = {
    'database': 'xxxxx',
    'user': 'xxxxx',
    'password': 'xxxxx',
    'host': 'xxxxx',
}

# Function to select unique names from database
def get_people():
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT name FROM pi_data.people ORDER BY name ASC")
    people_list = cur.fetchall()
    conn.close()
    return people_list

# Function to select unique countries from database
def get_country():
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT country FROM pi_data.pictures ORDER BY country ASC")
    country_list = [country[0] for country in cur.fetchall()]
    conn.close()
    return country_list

# Main screen for querying the database
@app.route('/', methods=['GET'])
def dropdown():
    people_list = get_people()
    country_list = get_country()
    return render_template('layout.html', people=people_list, countries=country_list)

# Route for images display
@app.route('/filter_images', methods=['POST'])
def filter_images():
    ################### Date filters ##########################
    # Extract the start and end date variables from the form
    start_date = request.form['start_date']
    end_date = request.form['end_date']

    # Set potential default values
    default_start_date = '1999-01-01' 
    default_end_date = date.today()

    # Check if start_date is not chosen or is an empty string
    if not start_date:
        start_date = default_start_date

    # Check if end_date is not chosen or is an empty string
    if not end_date:
        end_date = default_end_date

    ################### Country filters ##########################
    # Get the list of selected country codes from the submitted form
    selected_countries = request.form.getlist('countryfilter')

    country_list = get_country()
    # Convert the list to a comma-separated string
    if not selected_countries:
        selected_country_names = "', '".join(country_list) 
    else:
        selected_country_names = "', '".join(selected_countries) 

    ################### People filters ##########################
    # Create the filter_values list
    filter_values = []
    query_parts = []

    # Extract values from the people filter
    selected_people = request.form.getlist('peoplefilter')

    # Extract values from dynamically added person filters
    for i in range(len(selected_people)):
        alias = f"PE{i+1}"
        filter_values.append(f"{alias}.name = '{selected_people[i-1]}' AND")
        query_parts.append(f"INNER JOIN pi_data.person_picture AS PP{i+1} ON PP{i+1}.pictureid = PIC.id")
        query_parts.append(f"INNER JOIN pi_data.people AS {alias} ON {alias}.id = PP{i+1}.peopleid")
    
    ################### Text box filter ##########################
    user_string = request.form['tekst-box']

    # Append the filters from above
    # And construct the SQL query based on selected filters
    query_parts.append("WHERE 1 = 1 AND")
    query_parts.extend(filter_values)   
    query_parts.append(f"PIC.photo_taken BETWEEN '{start_date}' AND '{end_date}'")
    query_parts.append(f"AND PIC.country IN ('{selected_country_names}')")
    if user_string:
        query_parts.append(f"AND LOWER(PIC.file_name) LIKE LOWER('%{user_string}%')")

    # Build the SQL query from dynamic query parts
    sql_query = f"""
        SELECT PIC.id
        FROM pi_data.pictures AS PIC
        {' '.join(query_parts)}
    """
    print("SQL Query:", sql_query) # FOR DEBUGGING

    # Execute the SQL query
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute(sql_query)
    results = cur.fetchall()

    enumerated_images = [(i, image_id[0]) for i, image_id in enumerate(results)]
    return render_template('result.html', enumerated_images=enumerated_images)

# Implement the random picture button by fetching a random ID from the database and 
# loading image from render_image function through a new route
@app.route('/random-pic')
def random_picture():
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT id FROM pi_data.pictures ORDER BY RANDOM() LIMIT 1")
    random_image = cur.fetchone()[0]
    random_image_url = (f"/image/{random_image}")
    return jsonify({"imageUrl": random_image_url})

# Function to query the image binary content and retrieve it
def get_image_from_database(image_id):
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT content FROM pi_data.pictures WHERE id = %s", (image_id,))
    image_data = cur.fetchone()[0]
    conn.close()
    return image_data

# Function to render the image
def render_image(image_data):
    image = Image.open(BytesIO(image_data))
    output_buffer = BytesIO()
    image.save(output_buffer, format="JPEG")
    image_data = output_buffer.getvalue()
    return Response(image_data, content_type='image/jpeg')

# Create a route for each individual picture
@app.route('/image/<int:image_id>')
def show_image(image_id):
    image_data = get_image_from_database(image_id)
    return render_image(image_data)

if __name__ == '__main__':
    app.run(debug=True)