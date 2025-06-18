from setuptools import setup, find_packages

setup(
    name="certverify",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        alembic==1.13.1
        blinker==1.7.0
        click==8.1.7
        Flask==2.3.2
        Flask-Login==0.6.2
        Flask-Migrate==4.0.5
        Flask-SQLAlchemy==3.0.5  # Downgraded to match SQLAlchemy 1.4
        python-dotenv==1.0.0
        SQLAlchemy==1.4.48  # Downgraded to stable version
        Werkzeug==2.3.7
        qrcode==7.4.2
        Pillow==11.0.0 --only-binary=:all:
        qreader==3.16
        numpy==2.1.3  # Updated version for Python 3.13
        opencv-python-headless==4.9.0.80
        pyzbar==0.1.9
        gunicorn==21.2.0


    ],
)
