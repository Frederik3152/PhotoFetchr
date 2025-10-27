# Import libraries
from flask import Flask, render_template, request, Response, jsonify
import psycopg2
from PIL import Image
from io import BytesIO
from datetime import datetime
from config import config
import os
from werkzeug.utils import secure_filename
from pathlib import Path
import platform

app = Flask(__name__, static_folder='static')

# Set the global variable db_config as the database login credentials
db_config = config()

def get_photo_stats():
    """
    Get photo statistics from the database
    1. Total number of photos
    2. Total number of countries
    3. Total number of people
    4. Total storage used
    """
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    # Count total photos
    cursor.execute("SELECT COUNT(*) FROM photofetchr.pictures")
    total_photos = cursor.fetchone()[0]
    
    # Count countries
    cursor.execute("SELECT COUNT(DISTINCT country) FROM photofetchr.pictures WHERE country IS NOT NULL")
    total_countries = cursor.fetchone()[0]
    
    # Count people (adjust table name as needed)
    cursor.execute("SELECT COUNT(DISTINCT peopleid) FROM photofetchr.person_picture")
    total_people = cursor.fetchone()[0]
    
    # Calculate storage (adjust column names)
    cursor.execute("SELECT SUM(file_size) FROM photofetchr.pictures")
    storage_bytes = cursor.fetchone()[0] or 0
    storage_used = f"{round(storage_bytes / (1024 **3), 2)}GB"
    
    return {
        'total_photos': total_photos,
        'total_countries': total_countries, 
        'total_people': total_people,
        'storage_used': storage_used
    }

def get_recent_photos():
    """
    Show most recent photos from the database
    """
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, file_name, country, photo_taken, thumbnail_path
        FROM photofetchr.pictures 
        WHERE thumbnail_path IS NOT NULL
        ORDER BY photo_taken DESC 
        LIMIT 6
        """)
    rows = cursor.fetchall()
    conn.close()

    photos = []
    for row in rows:
        photo_id = row[0]
        file_name = row[1]
        country = row[2]
        photo_taken = row[3]
        thumb_path = row[4]

        photos.append({
            'id': photo_id,
            'title': file_name,
            'thumbnail_url': f"/thumbnail/{photo_id}",
            'location': country,
            'date_taken': photo_taken,
            })
     
    return photos

@app.route('/')
def homepage():
    # Get data needed for the homepage
    stats = get_photo_stats()
    recent_photos = get_recent_photos()
    return render_template('homepage.html', stats=stats, recent_photos=recent_photos)

@app.route('/search')
def search():
    # Get data needed for the search page
    people_list = get_people()
    country_list = get_country()
    search_query = request.args.get('q', '')
    return render_template('search.html', people=people_list, countries=country_list, search_query=search_query)

@app.route('/api/search', methods=['POST'])
def api_search():
    """
    Handle search requests from the search interface
    Returns JSON with search results
    """
    try:
        # Get JSON data from request
        data = request.get_json()

        # Extract search parameters
        search_text = data.get('search_text', '')
        countries = data.get('countries', [])
        people = data.get('people', [])
        date_from = data.get('date_from', '')
        date_to = data.get('date_to', '')
        sort_by = data.get('sort_by', 'date')

        # Build the search query
        results = search_photos(search_text, countries, people, date_from, date_to, sort_by)

        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@app.route('/api/photo/<int:photo_id>')
def api_photo_details(photo_id):
    """Get detailed information for a specific photo"""
    try:
        photo_details = get_photo_details(photo_id)
        if photo_details:
            return jsonify({
                'success': True,
                'photo': photo_details
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Photo not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def search_photos(search_text='', countries=[], people=[], date_from='', date_to='', sort_by='date'):
    """
    Enhanced search function that returns photo data for API
    """
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()

    # Base query
    query = """
        SELECT DISTINCT p.id, p.file_name, p.country, p.photo_taken, p.thumbnail_path, p.file_size
        FROM photofetchr.pictures p
    """

    # Add joins for people filter if needed
    joins = []
    conditions = ["1=1"]  # Always true base condition
    params = []

    # People filter
    if people:
        for i, person in enumerate(people):
            alias = f"pp{i}"
            joins.append(f"INNER JOIN photofetchr.person_picture {alias} ON {alias}.pictureid = p.id")
            joins.append(f"INNER JOIN photofetchr.people pe{i} ON pe{i}.id = {alias}.peopleid")
            conditions.append(f"pe{i}.name = %s")
            params.append(person)

    # Text search filter
    if search_text:
        conditions.append("LOWER(p.file_name) LIKE LOWER(%s)")
        params.append(f'%{search_text}%')

    # Country filter
    if countries:
        placeholders = ','.join(['%s'] * len(countries))
        conditions.append(f"p.country IN ({placeholders})")
        params.extend(countries)

    # Date filters
    if date_from:
        conditions.append("p.photo_taken >= %s")
        params.append(date_from)

    if date_to:
        conditions.append("p.photo_taken <= %s")
        params.append(date_to)

    # Construct final query
    if joins:
        query += " " + " ".join(joins)

    query += " WHERE " + " AND ".join(conditions)

    # Add sorting
    if sort_by == 'title':
        query += " ORDER BY p.file_name ASC"
    else:  # Default to date
        query += " ORDER BY p.photo_taken DESC"

    query += " LIMIT 100"

    # Execute query
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    # Format results for frontend
    photos = []
    for row in results:
        photos.append({
            'id': row[0],
            'title': row[1],
            'country': row[2],
            'date_taken': row[3].isoformat() if row[3] else None,
            'thumbnail_url': f"/thumbnail/{row[0]}",
            'file_size': row[5] if row[5] else 0
        })

    return photos

def get_photo_details(photo_id):
    """
    Get detailed information for a specific photo including people
    """
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()

    # Get photo details
    cursor.execute("""
        SELECT id, file_name, country, photo_taken, file_path, thumbnail_path, file_size
        FROM photofetchr.pictures
        WHERE id = %s
    """, (photo_id,))

    result = cursor.fetchone()
    if not result:
        conn.close()
        return None

    # Get people in photo
    cursor.execute("""
        SELECT pe.name
        FROM photofetchr.person_picture pp
        INNER JOIN photofetchr.people pe ON pe.id = pp.peopleid
        WHERE pp.pictureid = %s
        ORDER BY pe.name
    """, (photo_id,))

    people_results = cursor.fetchall()
    people = [person[0] for person in people_results]

    conn.close()

    # Format photo details
    photo = {
        'id': result[0],
        'title': result[1],
        'country': result[2],
        'date_taken': result[3].isoformat() if result[3] else None,
        'file_path': result[4],
        'thumbnail_path': result[5],
        'file_size': result[6] if result[6] else 0,
        'image_url': f"/image/{result[0]}",
        'thumbnail_url': f"/thumbnail/{result[0]}",
        'people': people
    }

    return photo

@app.template_filter('format_number')
def format_number(value):
    """
    Format numbers with commas
    """
    if isinstance(value, (int, float)):
        return f"{value:,}"
    return value

@app.template_filter('format_date')
def format_date(value):
    """
    Format datetime objects
    """
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    return value

@app.route('/api/people')
def api_people():
    """
    Return list of people in json format for checkbox population
    """
    people = get_people()
    # Convert tuple list to simple list of names
    people_names = [person[0] if isinstance(person, tuple) else person for person in people]
    return jsonify(people_names)

def get_people():
    """
    Get unique names from the database
    """
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT name FROM photofetchr.people ORDER BY name ASC")
    people_list = cur.fetchall()
    conn.close()
    return people_list

@app.route('/api/countries')
def api_countries():
    """
    Return list of countries in json format for dropdown population
    """
    countries = get_country()
    return jsonify(countries)

def get_country():
    """
    Get unique countries from the database
    """
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT country FROM photofetchr.pictures ORDER BY country ASC")
    country_list = [country[0] for country in cur.fetchall()]
    conn.close()
    return country_list

def get_image_from_filesystem(image_id):
    """
    Get image from filesystem instead of database
    """
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT file_path FROM photofetchr.pictures WHERE id = %s", (image_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if result and result[0]:
        if platform.system() == 'Windows':
            # Local Windows development
            thumbnail_path = result[0].replace('/photos/', r'C:\Files\Projects\PhotoFetchr Migration\photos_migration\\')
        else:
            # Production (Linux/Docker) - use path as stored in database
            thumbnail_path = result[0]
        
        # Check if file exists and return its contents
        if os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as f:
                return f.read()
    # return None

def get_thumbnail(image_id):
    """
    Get thumbnail from filesystem
    """
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    cur.execute("SELECT thumbnail_path FROM photofetchr.pictures WHERE id = %s", (image_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()

    if result and result[0]:
        if platform.system() == 'Windows':
            # Local Windows development
            thumbnail_path = result[0].replace('/photos/', r'C:\Files\Projects\PhotoFetchr Migration\photos_migration\\')
        else:
            # Production (Linux/Docker) - use path as stored in database
            thumbnail_path = result[0]
        
        # Check if file exists and return its contents
        if os.path.exists(thumbnail_path):
            with open(thumbnail_path, 'rb') as f:
                return f.read()
    # Fallback to original if no thumbnail
    return get_image_from_filesystem(image_id)


def render_image(image_data):
    """
    Render image from binary data
    """
    image = Image.open(BytesIO(image_data))
    output_buffer = BytesIO()
    image.save(output_buffer, format="JPEG")
    image_data = output_buffer.getvalue()
    return Response(image_data, content_type='image/jpeg')

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
        country = request.form.get('country', '').strip()
        people = request.form.getlist('people')
        custom_date = request.form.get('date', '').strip()
        
        # Validate mandatory country
        if not country:
            return jsonify([{'success': False, 'error': 'Country is required'}])
        
        # Parse custom date if provided
        photo_date = None
        if custom_date:
            try:
                photo_date = datetime.strptime(custom_date, '%Y-%m-%d').date()
            except ValueError:
                return jsonify([{'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}])
        
        results = []
        for file in files:
            if file and allowed_file(file.filename):
                result = add_photo_to_db(file, country, people, photo_date)
                results.append(result)
        
        return jsonify(results)
    
    # GET - show form
    people_list = get_people()
    country_list = get_country()
    return render_template('upload.html', people=people_list, countries=country_list)

def add_photo_to_db(file, country, people, custom_date=None):
    """
    Add single photo to database and filesystem
    """
    try:
        # Get next ID
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM photofetchr.pictures")
        photo_id = cur.fetchone()[0]
        
        # Use custom date or current date
        photo_date = custom_date if custom_date else datetime.now().date()
        
        # Generate paths using the photo date
        filename = f"{photo_date.strftime('%Y%m%d')}_{photo_id:06d}_{secure_filename(file.filename)}"
        
        original_path = f"/photos/originals/{photo_date.year}/{photo_date.month:02d}/{filename}"
        thumb_path = f"/photos/thumbnails/{photo_date.year}/{photo_date.month:02d}/thumb_{filename}"
        
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
            INSERT INTO photofetchr.pictures (id, file_name, country, photo_taken, file_path, thumbnail_path, file_size)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (photo_id, file.filename, country, photo_date, original_path, thumb_path, os.path.getsize(original_path)))
        
        # Add people
        for person_name in people:
            cur.execute("SELECT id FROM photofetchr.people WHERE name = %s", (person_name,))
            person_result = cur.fetchone()
            if person_result:
                cur.execute("INSERT INTO photofetchr.person_picture (peopleid, pictureid) VALUES (%s, %s)", 
                          (person_result[0], photo_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return {'success': True, 'filename': file.filename, 'id': photo_id, 'date': photo_date.isoformat()}
        
    except Exception as e:
        return {'success': False, 'filename': file.filename, 'error': str(e)}


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")