# Import libraries
from flask import Flask, render_template, request, Response
import psycopg2
from PIL import Image
from io import BytesIO

app = Flask(__name__)

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

# Main screen for querying the database
@app.route('/', methods=['GET'])
def dropdown():
    people_list = get_people()
    return render_template('layout.html', people=people_list)

# Route for images display
@app.route('/filter_images', methods=['POST'])
def filter_images():
    filter_values = []
    filter_count = request.form.get("filter_count")

    # Extract values from the default filter
    person_name = request.form['person_name']
    filter_values.append(f"PE1.name = '{person_name}'")

    # Extract values from dynamically added filters
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
