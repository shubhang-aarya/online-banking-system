from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.models import User, BankAccount, Transaction, LoanRequest
from app.decorators import login_required_api
from app.utils import generate_account_number
from datetime import datetime

user_bp = Blueprint('user', __name__, url_prefix='/api/user')

@user_bp.route('/profile', methods=['GET'])
@login_required_api
def get_profile():
    """Get user profile"""
    user = current_user
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'address': user.address,
        'pan_number': user.pan_number,
        'phone': user.phone,
        'created_at': user.created_at.isoformat()
    }), 200

@user_bp.route('/profile', methods=['PUT'])
@login_required_api
def update_profile():
    """Update user profile"""
    data = request.get_json()
    user = current_user
    
    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    if 'address' in data:
        user.address = data['address']
    if 'phone' in data:
        user.phone = data['phone']
    
    db.session.commit()
    
    return jsonify({'message': 'Profile updated successfully'}), 200

@user_bp.route('/accounts', methods=['GET'])
@login_required_api
def get_accounts():
    """Get all accounts of user"""
    accounts = BankAccount.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'accounts': [{
            'id': acc.id,
            'account_number': acc.account_number,
            'account_type': acc.account_type,
            'balance': acc.balance,
            'is_active': acc.is_active,
            'opening_date': acc.opening_date.isoformat()
        } for acc in accounts]
    }), 200

@user_bp.route('/account/create', methods=['POST'])
@login_required_api
def create_account():
    """Create new bank account"""
    data = request.get_json()
    
    if not data.get('account_type'):
        return jsonify({'error': 'Account type required'}), 400
    
    account = BankAccount(
        account_number=generate_account_number(),
        account_type=data['account_type'],
        balance=0.0,
        user_id=current_user.id,
        is_active=True
    )
    
    db.session.add(account)
    db.session.commit()
    
    return jsonify({
        'message': 'Account created successfully',
        'account': {
            'id': account.id,
            'account_number': account.account_number,
            'account_type': account.account_type,
            'balance': account.balance,
            'opening_date': account.opening_date.isoformat()
        }
    }), 201

@user_bp.route('/transaction/deposit', methods=['POST'])
@login_required_api
def request_deposit():
    """Request deposit"""
    data = request.get_json()
    
    if not data.get('account_id') or not data.get('amount'):
        return jsonify({'error': 'Account ID and amount required'}), 400
    
    account = BankAccount.query.filter_by(id=data['account_id'], user_id=current_user.id).first()
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    if data['amount'] <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400
    
    transaction = Transaction(
        account_id=account.id,
        user_id=current_user.id,
        transaction_type='deposit',
        amount=data['amount'],
        status='pending',
        description=data.get('description', '')
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'message': 'Deposit request submitted',
        'transaction': {
            'id': transaction.id,
            'transaction_id': transaction.transaction_id,
            'amount': transaction.amount,
            'status': transaction.status,
            'requested_at': transaction.requested_at.isoformat()
        }
    }), 201

@user_bp.route('/transaction/withdraw', methods=['POST'])
@login_required_api
def request_withdraw():
    """Request withdrawal"""
    data = request.get_json()
    
    if not data.get('account_id') or not data.get('amount'):
        return jsonify({'error': 'Account ID and amount required'}), 400
    
    account = BankAccount.query.filter_by(id=data['account_id'], user_id=current_user.id).first()
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    if data['amount'] <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400
    
    transaction = Transaction(
        account_id=account.id,
        user_id=current_user.id,
        transaction_type='withdraw',
        amount=data['amount'],
        status='pending',
        description=data.get('description', '')
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'message': 'Withdrawal request submitted',
        'transaction': {
            'id': transaction.id,
            'transaction_id': transaction.transaction_id,
            'amount': transaction.amount,
            'status': transaction.status,
            'requested_at': transaction.requested_at.isoformat()
        }
    }), 201

@user_bp.route('/transactions', methods=['GET'])
@login_required_api
def get_transactions():
    """Get user transactions"""
    account_id = request.args.get('account_id')
    
    query = Transaction.query.filter_by(user_id=current_user.id)
    if account_id:
        query = query.filter_by(account_id=account_id)
    
    transactions = query.order_by(Transaction.requested_at.desc()).all()
    
    return jsonify({
        'transactions': [{
            'id': t.id,
            'transaction_id': t.transaction_id,
            'type': t.transaction_type,
            'amount': t.amount,
            'status': t.status,
            'requested_at': t.requested_at.isoformat(),
            'processed_at': t.processed_at.isoformat() if t.processed_at else None
        } for t in transactions]
    }), 200

@user_bp.route('/loan/request', methods=['POST'])
@login_required_api
def request_loan():
    """Request loan"""
    data = request.get_json()
    
    required_fields = ['amount', 'purpose', 'duration_months']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if data['amount'] <= 0:
        return jsonify({'error': 'Loan amount must be positive'}), 400
    
    if data['duration_months'] <= 0:
        return jsonify({'error': 'Duration must be positive'}), 400
    
    loan = LoanRequest(
        user_id=current_user.id,
        amount=data['amount'],
        purpose=data['purpose'],
        duration_months=data['duration_months'],
        status='pending'
    )
    
    db.session.add(loan)
    db.session.commit()
    
    return jsonify({
        'message': 'Loan request submitted',
        'loan': {
            'id': loan.id,
            'loan_id': loan.loan_id,
            'amount': loan.amount,
            'status': loan.status,
            'requested_at': loan.requested_at.isoformat()
        }
    }), 201

@user_bp.route('/loans', methods=['GET'])
@login_required_api
def get_loans():
    """Get user loan requests"""
    loans = LoanRequest.query.filter_by(user_id=current_user.id).order_by(LoanRequest.requested_at.desc()).all()
    
    return jsonify({
        'loans': [{
            'id': l.id,
            'loan_id': l.loan_id,
            'amount': l.amount,
            'purpose': l.purpose,
            'duration_months': l.duration_months,
            'status': l.status,
            'interest_rate': l.interest_rate,
            'requested_at': l.requested_at.isoformat(),
            'processed_at': l.processed_at.isoformat() if l.processed_at else None
        } for l in loans]
    }), 200

@user_bp.route('/account/<int:account_id>', methods=['DELETE'])
@login_required_api
def delete_account(account_id):
    """Delete/dissolve account"""
    account = BankAccount.query.filter_by(id=account_id, user_id=current_user.id).first()
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    if account.balance > 0:
        return jsonify({'error': 'Cannot delete account with non-zero balance'}), 400
    
    account.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'Account deleted successfully'}), 200