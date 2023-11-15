# Import libraries
from flask import Flask, render_template, request, Response
import psycopg2
from PIL import Image
from io import BytesIO
from datetime import date
from country_mapping import country_mapping

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
    cur.execute("SELECT DISTINCT name FROM pi_data.people")
    people_list = cur.fetchall()
    conn.close()
    return people_list

# Function to select unique countries from database
def get_country():
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT country FROM pi_data.pictures")
    country_list = [country[0] for country in cur.fetchall()]
    conn.close()
    return country_list

# Main screen for querying the database
@app.route('/', methods=['GET'])
def dropdown():
    people_list = get_people()
    country_list = get_country()
    country_codes = [country_mapping.get(name) for name in country_list if country_mapping.get(name)]
    data_countries = ','.join(country_codes)
    return render_template('layout.html', people=people_list, data_countries=data_countries)

# Route for images display
@app.route('/filter_images', methods=['POST'])
def filter_images():
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

    # Get the list of selected country codes from the submitted form
    selected_countries = request.form.getlist('countries')

    # Create a reverse mapping where keys are country codes and values are country names
    reverse_country_mapping = {v: k for k, v in country_mapping.items()}

    # Use the reverse mapping to convert the list of selected country codes back to country names
    selected_country_names = [reverse_country_mapping.get(code) for code in selected_countries]

    # Convert the list to a comma-separated string
    selected_country_names = "', '".join(selected_country_names)

    # Get the filter count variable from the javascript function, counting how many person filters where inserted
    filter_values = []
    filter_count = request.form.get("filter_count")
    
    # Extract values from the default person filter
    person_name = request.form['person_name']
    filter_values.append(f"PE1.name = '{person_name}'")

    # Extract values from dynamically added person filters
    for filter_id in range(2, int(filter_count)+2):
        filter_value = request.form.get(f'filter_{filter_id - 1}')
        if filter_value:
            alias = f"AND PE{filter_id}"
            filter_values.append(f"{alias}.name = '{filter_value}'")

    # Construct the SQL query based on selected filters
    query_parts = []

    for i in range(1, int(filter_count)+1):
        alias = f"PE{i}"
        query_parts.append(f"INNER JOIN pi_data.person_picture AS PP{i} ON PP{i}.pictureid = PIC.id")
        query_parts.append(f"INNER JOIN pi_data.people AS {alias} ON {alias}.id = PP{i}.peopleid")

    # Append the "WHERE" and "PE{i}" filters
    query_parts.append("WHERE 1 = 1 AND")
    query_parts.extend(filter_values)   
    query_parts.append(f"AND PIC.photo_taken BETWEEN '{start_date}' AND '{end_date}'")
    query_parts.append(f"AND PIC.country IN ('{selected_country_names}')")

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