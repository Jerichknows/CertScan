from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import qrcode
from io import BytesIO
import base64
from datetime import datetime
import cv2
import numpy as np
from pyzbar.pyzbar import decode

__version__ = "1.0.0"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///certificates.db').replace("postgres://", "postgresql://")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    issue_date = db.Column(db.String(20), nullable=False)
    certificate_id = db.Column(db.String(50), unique=True, nullable=False)
    qr_code = db.Column(db.String(500), nullable=False)
    qr_filename = db.Column(db.String(100))
    is_verified = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Certificate {self.certificate_id}>'

# Create database tables
with app.app_context():
    db.create_all()

def generate_qr_code(data):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Save QR code to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{qr_code_data}"
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/issue', methods=['GET', 'POST'])
def issue_certificate():
    if request.method == 'POST':
        student_name = request.form.get('student_name', '').strip()
        course_name = request.form.get('course_name', '').strip()

        if not student_name or not course_name:
            return render_template('issue_form.html', error="Please fill all fields")

        issue_date = datetime.now().strftime('%Y-%m-%d')
        certificate_id = f"CID-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Generate verification URL
        verification_url = url_for('verify_certificate', cert_id=certificate_id, _external=True)

        # Generate QR code
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(verification_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Save to BytesIO buffer for base64
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
            qr_code_data = f"data:image/png;base64,{qr_code_base64}"

            # Save to file
            qr_filename = f"{certificate_id}.png"
            qr_path = os.path.join(app.config['UPLOAD_FOLDER'], qr_filename)
            img.save(qr_path)

        except Exception as e:
            return render_template('issue_form.html', error=f"QR Generation Error: {str(e)}")

        # Save to database
        try:
            new_cert = Certificate(
                student_name=student_name,
                course_name=course_name,
                issue_date=issue_date,
                certificate_id=certificate_id,
                qr_code=qr_code_data,
                qr_filename=qr_filename
            )

            db.session.add(new_cert)
            db.session.commit()

            return render_template('certificate_issued.html',
                                student_name=student_name,
                                course_name=course_name,
                                issue_date=issue_date,
                                certificate_id=certificate_id,
                                qr_code=qr_code_data,
                                verification_url=verification_url)
        except Exception as e:
            db.session.rollback()
            if 'qr_path' in locals() and os.path.exists(qr_path):
                os.remove(qr_path)
            return render_template('issue_form.html', error=f"Database error: {str(e)}")

    return render_template('issue_form.html')

@app.route('/verify/<cert_id>')
def verify_certificate(cert_id):
    certificate = Certificate.query.filter_by(certificate_id=cert_id).first()

    if certificate:
        certificate.is_verified = True
        db.session.commit()
        return render_template('verification_result.html',
                             valid=True,
                             student_name=certificate.student_name,
                             course_name=certificate.course_name,
                             issue_date=certificate.issue_date,
                             certificate_id=certificate.certificate_id)
    else:
        return render_template('verification_result.html', valid=False)

@app.route('/check', methods=['GET', 'POST'])
def check_certificate():
    if request.method == 'POST':
        certificate_id = request.form.get('certificate_id', '').strip()
        if not certificate_id:
            return render_template('check_form.html', error="Please enter a certificate ID")

        certificate = Certificate.query.filter_by(certificate_id=certificate_id).first()

        if certificate:
            return render_template('check_result.html',
                                 found=True,
                                 certificate=certificate)
        else:
            return render_template('check_result.html', found=False)

    return render_template('check_form.html')

@app.route('/verify-qr', methods=['POST'])
def verify_qr_certificate():
    if 'qr_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['qr_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # Read the image file
        img_bytes = file.read()
        np_img = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        # Decode QR code
        decoded_objects = decode(img)
        if not decoded_objects:
            return jsonify({'error': 'No QR code found'}), 400

        # Get the first QR code data
        qr_data = decoded_objects[0].data.decode('utf-8')

        # Extract certificate ID from URL
        if '/verify/' in qr_data:
            cert_id = qr_data.split('/verify/')[-1].strip()
            certificate = Certificate.query.filter_by(certificate_id=cert_id).first()

            if certificate:
                return jsonify({
                    'valid': True,
                    'certificate_id': certificate.certificate_id,
                    'student_name': certificate.student_name,
                    'course_name': certificate.course_name,
                    'issue_date': certificate.issue_date,
                    'is_verified': certificate.is_verified
                })

        return jsonify({'error': 'Invalid QR code or certificate not found'}), 400

    except Exception as e:
        return jsonify({'error': f'Error processing QR code: {str(e)}'}), 500

@app.route('/certificates')
def list_certificates():
    certificates = Certificate.query.order_by(Certificate.issue_date.desc()).all()
    return render_template('certificates_list.html', certificates=certificates)

@app.route('/certificates/unverified')
def unverified_certificates():
    certificates = Certificate.query.filter_by(is_verified=False)\
                     .order_by(Certificate.issue_date.desc()).all()
    return render_template('certificates_list.html',
                         certificates=certificates,
                         title="Unverified Certificates")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
