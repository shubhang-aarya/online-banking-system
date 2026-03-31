from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User
import re

auth_bp = Blueprint('auth', __name__)

def validate_pan(pan):
    """Validate PAN format"""
    pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    return re.match(pan_pattern, pan) is not None

def validate_email(email):
    """Validate email format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

@auth_bp.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json() if request.is_json else request.form
    
    # Validate input
    if not all(key in data for key in ['username', 'email', 'password', 'first_name', 'last_name', 'address', 'pan_number', 'phone']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if len(data['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    if not validate_email(data['email']):
        return jsonify({'error': 'Invalid email format'}), 400
    
    if not validate_pan(data['pan_number'].upper()):
        return jsonify({'error': 'Invalid PAN format (e.g., AAAAA0000A)'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    if User.query.filter_by(pan_number=data['pan_number'].upper()).first():
        return jsonify({'error': 'PAN number already exists'}), 400
    
    # Create new user
    user = User(
        username=data['username'],
        email=data['email'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        address=data['address'],
        pan_number=data['pan_number'].upper(),
        phone=data['phone'],
        role='user'
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully', 'user_id': user.id}), 201


@auth_bp.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json() if request.is_json else request.form
    
    if not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is inactive'}), 403
    
    login_user(user)
    
    return jsonify({
        'message': 'Login successful',
        'user_id': user.id,
        'username': user.username,
        'role': user.role
    }), 200


@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    """Logout user"""
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200