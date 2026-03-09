import pytest
import os
import sqlite3
import app as system_app

@pytest.fixture
def test_db(monkeypatch, tmp_path):
    """
    Creates a temporary database for testing and overrides the app's DB_FILE.
    """
    db_path = tmp_path / "test_database.db"
    # Overwrite the database file path so tests don't affect existing data
    monkeypatch.setattr(system_app, 'DB_FILE', str(db_path))
    
    # Initialize the tables by getting a connection
    conn = system_app.get_db_connection()
    conn.close()
    
    yield str(db_path)
    
    # Cleanup after tests
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass

@pytest.fixture
def client(test_db):
    """
    Flask test client that uses the temporary database.
    """
    system_app.app.config['TESTING'] = True
    with system_app.app.test_client() as client:
        yield client

def test_fee_calculation_single_document(client, test_db):
    """Check correct fee calculation for each document type."""
    # Test for a single document: Transcript of Records (₱90)
    response = client.post('/request', data={
        'full_name': 'Test User',
        'student_number': '12345',
        'department': 'CS',
        'program': 'BSCS',
        'qty_Transcript_of_Records': '1'
    })
    
    # It should redirect to the result page upon success
    assert response.status_code == 302
    
    # Check the database to see if the amount was calculated correctly
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    req = conn.execute('SELECT * FROM requests ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    
    assert req is not None
    assert req['total_amount'] == 90
    assert '1x Transcript of Records' in req['documents_requested']

def test_fee_calculation_multiple_quantities(client, test_db):
    """Check multiple quantity calculations (ex. 3 TOR = ₱270)."""
    # Note: Using the actual price from app.py (90 for TOR)
    response = client.post('/request', data={
        'full_name': 'Test User Multi',
        'student_number': '54321',
        'department': 'IT',
        'program': 'BSIT',
        'qty_Transcript_of_Records': '3'
    })
    
    assert response.status_code == 302
    
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    req = conn.execute('SELECT * FROM requests ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    
    assert req['total_amount'] == 270
    assert '3x Transcript of Records' in req['documents_requested']

def test_fee_calculation_multiple_documents(client, test_db):
    """Check calculation of mixed document requests."""
    # Test mixed items: 
    # 2x Transcript of Records (2 * 90 = 180)
    # 1x Certification (1 * 130 = 130)
    # 1x Documentary Stamp (1 * 50 = 50)
    # Total = 360
    response = client.post('/request', data={
        'full_name': 'Mixed Docs',
        'student_number': '11111',
        'department': 'CS',
        'program': 'BSCS',
        'qty_Transcript_of_Records': '2',
        'qty_Certification': '1',
        'stamp_qty': '1'
    })
    
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    req = conn.execute('SELECT * FROM requests ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    
    assert req['total_amount'] == 360
    assert '2x Transcript of Records' in req['documents_requested']
    assert '1x Certification' in req['documents_requested']
    assert '1x Documentary Stamp' in req['documents_requested']

def test_invalid_document_handling(client, test_db):
    """Check invalid document handling."""
    # Pass an invalid document type in the form that the system doesn't know
    # Along with a valid one
    response = client.post('/request', data={
        'full_name': 'Invalid Doc User',
        'student_number': '22222',
        'department': 'CS',
        'program': 'BSCS',
        'qty_Transcript_of_Records': '1',
        'qty_Invalid_Document': '5'
    })
    
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    req = conn.execute('SELECT * FROM requests ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    
    # The invalid document should be completely ignored; total should only be for valid ones
    assert req['total_amount'] == 90
    assert 'Invalid' not in req['documents_requested']

def test_queue_number_generation_logic(client, test_db):
    """Check correct queue number generation throughout a sequence of requests."""
    # Submit first request
    client.post('/request', data={
        'full_name': 'User One',
        'student_number': '101',
        'department': 'CS',
        'program': 'BSCS',
        'qty_Transcript_of_Records': '1'
    })
    
    # Submit second request
    client.post('/request', data={
        'full_name': 'User Two',
        'student_number': '102',
        'department': 'CS',
        'program': 'BSCS',
        'qty_Transcript_of_Records': '1'
    })
    
    conn = sqlite3.connect(test_db)
    conn.row_factory = sqlite3.Row
    requests = conn.execute('SELECT queue_number FROM requests ORDER BY id ASC').fetchall()
    conn.close()
    
    assert len(requests) == 2
    assert requests[0]['queue_number'] == 'SR00001'
    assert requests[1]['queue_number'] == 'SR00002'

def test_generate_queue_number_function(test_db):
    """Unit test checking the queue number generation logic directly without routing."""
    conn = system_app.get_db_connection()
    
    # It should start with SR00001 if empty
    q1 = system_app.generate_queue_number(conn)
    assert q1 == 'SR00001'
    
    # Insert a record directly simulating an existing SR00005 to check continuity
    conn.execute(
        "INSERT INTO requests (queue_number, full_name, student_number, department, program, documents_requested, total_amount) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ('SR00005', 'Test Data', '123', 'CS', 'BSCS', 'Doc', 100)
    )
    conn.commit()
    
    # The next queue block should jump to SR00006
    q2 = system_app.generate_queue_number(conn)
    assert q2 == 'SR00006'
    
    conn.close()
