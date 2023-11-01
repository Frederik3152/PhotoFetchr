# Import libraries
from flask import Flask, render_template, request, Response
import psycopg2
from PIL import Image
from io import BytesIO

app = Flask(__name__)

# Database configuration
db_config = {
    'database': 'xxxxxxx',
    'user': 'xxxxxx',
    'password': 'xxxxxx',
    'host': 'xxxxxx',
}

# Function to query the database and retrieve the image
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

# Function to select unique names from database
def get_people():
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT name FROM pi_data.people")
    people_list = cur.fetchall()
    conn.close()
    return people_list


@app.route('/', methods=['GET'])
def dropdown():
    people_list = get_people()
    return render_template('layout.html', people=people_list)

# Create a route for your web application
@app.route('/image/<int:image_id>')
def show_image(image_id):
    image_data = get_image_from_database(image_id)
    return render_image(image_data)

if __name__ == '__main__':
    app.run(debug=True)


