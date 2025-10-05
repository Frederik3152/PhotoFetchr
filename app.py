# Import libraries
from flask import Flask, render_template, request, Response, jsonify
import psycopg2
from PIL import Image
from io import BytesIO
from datetime import date, datetime
from config import config
import os
from werkzeug.utils import secure_filename
from pathlib import Path
import shutil

app = Flask(__name__, static_folder='static')

# Set the global variable db_config as the database login credentials
db_config = config()

# Function to select unique names from database
def get_people():
    """
    Get unique names from the database
    """
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT name FROM pi_data.people ORDER BY name ASC")
    people_list = cur.fetchall()
    conn.close()
    return people_list

# Function to select unique countries from database
def get_country():
    """
    Get unique countries from the database
    """
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT country FROM pi_data.pictures ORDER BY country ASC")
    country_list = [country[0] for country in cur.fetchall()]
    conn.close()
    return country_list

# Main screen for querying the database
@app.route('/', methods=['GET'])
def dropdown():
    """
    Render the main layout with dropdowns for people and countries
    """
    people_list = get_people()
    country_list = get_country()
    return render_template('layout.html', people=people_list, countries=country_list)

# Route for images display
@app.route('/filter_images', methods=['POST'])
def filter_images():
    """
    Filter images based on user input and display results
    """
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
    query_parts.append("LIMIT 100;")

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
    """
    Fetch a random picture ID from the database and return its URL
    """
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT id FROM pi_data.pictures WHERE file_path IS NOT NULL ORDER BY RANDOM() LIMIT 1")
    result = cur.fetchone()
    conn.close()
    
    if result:
        random_image = result[0]
        random_image_url = f"/image/{random_image}"
        return jsonify({"imageUrl": random_image_url})
    else:
        return jsonify({"error": "No images found"}), 404

def get_image_from_filesystem(image_id):
    """
    Get image from filesystem instead of database
    """
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT file_path FROM pi_data.pictures WHERE id = %s", (image_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result and result[0] and os.path.exists(result[0]):
        with open(result[0], 'rb') as f:
            return f.read()
    return None

def get_thumbnail(image_id):
    """
    Get thumbnail from filesystem
    """
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT thumbnail_path FROM pi_data.pictures WHERE id = %s", (image_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result and result[0] and os.path.exists(result[0]):
        with open(result[0], 'rb') as f:
            return f.read()
    # Fallback to original if no thumbnail
    return get_image_from_filesystem(image_id)


# Function to render the image
def render_image(image_data):
    """
    Render image from binary data
    """
    image = Image.open(BytesIO(image_data))
    output_buffer = BytesIO()
    image.save(output_buffer, format="JPEG")
    image_data = output_buffer.getvalue()
    return Response(image_data, content_type='image/jpeg')

# Create a route for each individual picture
@app.route('/image/<int:image_id>')
def show_image(image_id):
    """
    Show image by ID
    """
    image_data = get_image_from_filesystem(image_id)
    if image_data:
        return render_image(image_data)
    else:
        return "Image not found", 404
    
@app.route('/thumbnail/<int:image_id>')
def show_thumbnail(image_id):
    """
    Show thumbnail by ID
    """
    image_data = get_thumbnail(image_id)
    if image_data:
        return render_image(image_data)  
    else:
        return "Thumbnail not found", 404
    
# Simple upload configuration
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        files = request.files.getlist('photos')
        country = request.form.get('country', '')
        people = request.form.getlist('people')
        
        results = []
        for file in files:
            if file and allowed_file(file.filename):
                result = add_photo_to_db(file, country, people)
                results.append(result)
        
        return jsonify(results)
    
    # GET - show form
    people_list = get_people()
    return render_template('upload.html', people=people_list)

def add_photo_to_db(file, country, people):
    """
    Add single photo to database and filesystem
    """
    try:
        # Get next ID
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM pi_data.pictures")
        photo_id = cur.fetchone()[0]
        
        # Generate paths
        now = datetime.now()
        filename = f"{now.strftime('%Y%m%d')}_{photo_id:06d}_{secure_filename(file.filename)}"
        
        original_path = f"/photos/originals/{now.year}/{now.month:02d}/{filename}"
        thumb_path = f"/photos/thumbnails/{now.year}/{now.month:02d}/thumb_{filename}"
        
        # Create directories and save files
        Path(original_path).parent.mkdir(parents=True, exist_ok=True)
        Path(thumb_path).parent.mkdir(parents=True, exist_ok=True)
        
        file.save(original_path)
        
        # Create thumbnail
        with Image.open(original_path) as img:
            img.thumbnail((300, 300))
            img.save(thumb_path, "JPEG", quality=85)
        
        # Save to database
        cur.execute("""
            INSERT INTO pi_data.pictures (id, file_name, country, photo_taken, file_path, thumbnail_path, file_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (photo_id, file.filename, country, now.date(), original_path, thumb_path, os.path.getsize(original_path)))
        
        # Add people
        for person_name in people:
            cur.execute("SELECT id FROM pi_data.people WHERE name = %s", (person_name,))
            person_result = cur.fetchone()
            if person_result:
                cur.execute("INSERT INTO pi_data.person_picture (peopleid, pictureid) VALUES (%s, %s)", 
                          (person_result[0], photo_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {'success': True, 'filename': file.filename, 'id': photo_id}
        
    except Exception as e:
        return {'success': False, 'filename': file.filename, 'error': str(e)}


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")