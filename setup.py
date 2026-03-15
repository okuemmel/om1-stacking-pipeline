"""
py2app setup script for OM-1 Stacking Pipeline
Minimal setup.py - all metadata in pyproject.toml
"""
# In setup.py ergänzen:
import os
from pathlib import Path

# Find Flask package location
import flask
flask_path = Path(flask.__file__).parent

DATA_FILES = [
    ('examples', ['examples/config_default.yaml']),
]

# Add Flask's templates if they exist
flask_templates = flask_path / 'templates'
if flask_templates.exists():
    DATA_FILES.append(('flask/templates', [str(f) for f in flask_templates.glob('*')]))
    
from setuptools import setup

APP = ['macro_stacking_web.py']
APP_NAME = 'OM-1 Stacking Pipeline'

DATA_FILES = [
    ('examples', ['examples/config_default.yaml']),
]

OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'resources/app_icon.icns',
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleGetInfoString': 'OM-1 Macro Focus Stacking Pipeline',
        'CFBundleIdentifier': 'com.okuemmel.om1-stacking-pipeline',
        'CFBundleVersion': '4.1.0',
        'CFBundleShortVersionString': '4.1.0',
        'NSHumanReadableCopyright': 'Copyright © 2026 Oliver Kümmel',
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Olympus RAW Image',
                'CFBundleTypeRole': 'Viewer',
                'LSItemContentTypes': ['com.olympus.raw-image'],
                'LSHandlerRank': 'Alternate',
            }
        ],
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
        'LSApplicationCategoryType': 'public.app-category.photography',
        'NSRequiresAquaSystemAppearance': False,
    },
    'packages': [
         'flask',
        'flask_socketio',
        'socketio',
        'engineio',
        'simple_websocket',  # ← Oft vergessen!
        'wsproto',           # ← Auch wichtig
        'PIL',
        'yaml',
 
    ],
    'includes': [
        'webbrowser',
        'threading',
        'subprocess',
        'pathlib',
        'hashlib',
        'base64',
        'io',
        'time',
        'datetime',
        'logging',
    ],
    'excludes': [
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'tkinter',
        'test',
        'unittest',
    ],
    'resources': [
        'examples/config_default.yaml',
    ],
    'optimize': 2,
    'compressed': True,
    'strip': True,
}

# WICHTIG: Keine install_requires, version, author, etc. mehr!
# Alles kommt aus pyproject.toml
setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
)
