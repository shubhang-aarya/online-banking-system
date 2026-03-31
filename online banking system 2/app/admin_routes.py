from flask import Blueprint, request, jsonify
from flask_login import current_user
from app import db
from app.models import User, BankAccount, Transaction, LoanRequest
from app.decorators import admin_required, login_required_api
from datetime import datetime

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users with their account details"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    users = User.query.filter_by(role='user').paginate(page=page, per_page=per_page)
    
    users_data = []
    for user in users.items:
        accounts = BankAccount.query.filter_by(user_id=user.id).all()
        users_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'address': user.address,
            'pan_number': user.pan_number,
            'phone': user.phone,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat(),
            'accounts': [{
                'id': acc.id,
                'account_number': acc.account_number,
                'account_type': acc.account_type,
                'balance': acc.balance,
                'is_active': acc.is_active,
                'opening_date': acc.opening_date.isoformat()
            } for acc in accounts]
        })
    
    return jsonify({
        'users': users_data,
        'total': users.total,
        'pages': users.pages,
        'current_page': page
    }), 200

@admin_bp.route('/user/<int:user_id>', methods=['GET'])
@admin_required
def get_user_details(user_id):
    """Get detailed user information"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    accounts = BankAccount.query.filter_by(user_id=user.id).all()
    transactions = Transaction.query.filter_by(user_id=user.id).all()
    loans = LoanRequest.query.filter_by(user_id=user.id).all()
    
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'address': user.address,
            'pan_number': user.pan_number,
            'phone': user.phone,
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat(),
            'total_balance': sum(acc.balance for acc in accounts),
            'account_count': len(accounts),
            'transaction_count': len(transactions),
            'loan_count': len(loans)
        },
        'accounts': [{
            'id': acc.id,
            'account_number': acc.account_number,
            'account_type': acc.account_type,
            'balance': acc.balance,
            'is_active': acc.is_active,
            'opening_date': acc.opening_date.isoformat()
        } for acc in accounts]
    }), 200

@admin_bp.route('/transactions/pending', methods=['GET'])
@admin_required
def get_pending_transactions():
    """Get all pending transactions"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    transactions = Transaction.query.filter_by(status='pending').paginate(page=page, per_page=per_page)
    
    return jsonify({
        'transactions': [{
            'id': t.id,
            'transaction_id': t.transaction_id,
            'user': {
                'id': t.user.id,
                'username': t.user.username,
                'email': t.user.email
            },
            'account_number': t.account.account_number,
            'type': t.transaction_type,
            'amount': t.amount,
            'status': t.status,
            'requested_at': t.requested_at.isoformat()
        } for t in transactions.items],
        'total': transactions.total,
        'pages': transactions.pages,
        'current_page': page
    }), 200

@admin_bp.route('/transaction/<int:transaction_id>/approve', methods=['POST'])
@admin_required
def approve_transaction(transaction_id):
    """Approve transaction"""
    transaction = Transaction.query.get(transaction_id)
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    if transaction.status != 'pending':
        return jsonify({'error': 'Transaction is not pending'}), 400
    
    account = transaction.account
    
    # Check fund availability for withdrawal
    if transaction.transaction_type == 'withdraw' and account.balance < transaction.amount:
        return jsonify({'error': 'Insufficient funds in account'}), 400
    
    # Process transaction
    if transaction.transaction_type == 'deposit':
        account.balance += transaction.amount
    else:  # withdraw
        account.balance -= transaction.amount
    
    transaction.status = 'approved'
    transaction.processed_at = datetime.utcnow()
    transaction.processed_by = current_user.id
    
    db.session.commit()
    
    return jsonify({
        'message': 'Transaction approved',
        'transaction': {
            'id': transaction.id,
            'status': transaction.status,
            'processed_at': transaction.processed_at.isoformat()
        }
    }), 200

@admin_bp.route('/transaction/<int:transaction_id>/reject', methods=['POST'])
@admin_required
def reject_transaction(transaction_id):
    """Reject transaction"""
    data = request.get_json()
    transaction = Transaction.query.get(transaction_id)
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    if transaction.status != 'pending':
        return jsonify({'error': 'Transaction is not pending'}), 400
    
    transaction.status = 'rejected'
    transaction.processed_at = datetime.utcnow()
    transaction.processed_by = current_user.id
    
    if data.get('remarks'):
        transaction.description = f"Rejected: {data['remarks']}"
    
    db.session.commit()
    
    return jsonify({
        'message': 'Transaction rejected',
        'transaction': {
            'id': transaction.id,
            'status': transaction.status,
            'processed_at': transaction.processed_at.isoformat()
        }
    }), 200

@admin_bp.route('/loans/pending', methods=['GET'])
@admin_required
def get_pending_loans():
    """Get all pending loan requests"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    loans = LoanRequest.query.filter_by(status='pending').paginate(page=page, per_page=per_page)
    
    return jsonify({
        'loans': [{
            'id': l.id,
            'loan_id': l.loan_id,
            'user': {
                'id': l.user.id,
                'username': l.user.username,
                'email': l.user.email,
                'pan_number': l.user.pan_number
            },
            'amount': l.amount,
            'purpose': l.purpose,
            'duration_months': l.duration_months,
            'status': l.status,
            'requested_at': l.requested_at.isoformat()
        } for l in loans.items],
        'total': loans.total,
        'pages': loans.pages,
        'current_page': page
    }), 200

@admin_bp.route('/loan/<int:loan_id>/approve', methods=['POST'])
@admin_required
def approve_loan(loan_id):
    """Approve loan request"""
    data = request.get_json()
    loan = LoanRequest.query.get(loan_id)
    
    if not loan:
        return jsonify({'error': 'Loan request not found'}), 404
    
    if loan.status != 'pending':
        return jsonify({'error': 'Loan is not pending'}), 400
    
    loan.status = 'approved'
    loan.processed_at = datetime.utcnow()
    loan.processed_by = current_user.id
    loan.interest_rate = data.get('interest_rate', 8.5)
    loan.remarks = data.get('remarks', '')
    
    db.session.commit()
    
    return jsonify({
        'message': 'Loan approved',
        'loan': {
            'id': loan.id,
            'loan_id': loan.loan_id,
            'status': loan.status,
            'interest_rate': loan.interest_rate,
            'processed_at': loan.processed_at.isoformat()
        }
    }), 200

@admin_bp.route('/loan/<int:loan_id>/reject', methods=['POST'])
@admin_required
def reject_loan(loan_id):
    """Reject loan request"""
    data = request.get_json()
    loan = LoanRequest.query.get(loan_id)
    
    if not loan:
        return jsonify({'error': 'Loan request not found'}), 404
    
    if loan.status != 'pending':
        return jsonify({'error': 'Loan is not pending'}), 400
    
    loan.status = 'rejected'
    loan.processed_at = datetime.utcnow()
    loan.processed_by = current_user.id
    loan.remarks = data.get('remarks', '')
    
    db.session.commit()
    
    return jsonify({
        'message': 'Loan rejected',
        'loan': {
            'id': loan.id,
            'loan_id': loan.loan_id,
            'status': loan.status,
            'processed_at': loan.processed_at.isoformat()
        }
    }), 200

@admin_bp.route('/dashboard/stats', methods=['GET'])
@admin_required
def get_dashboard_stats():
    """Get dashboard statistics"""
    total_users = User.query.filter_by(role='user').count()
    total_accounts = BankAccount.query.count()
    total_balance = db.session.query(db.func.sum(BankAccount.balance)).scalar() or 0
    
    pending_transactions = Transaction.query.filter_by(status='pending').count()
    approved_transactions = Transaction.query.filter_by(status='approved').count()
    rejected_transactions = Transaction.query.filter_by(status='rejected').count()
    
    pending_loans = LoanRequest.query.filter_by(status='pending').count()
    approved_loans = LoanRequest.query.filter_by(status='approved').count()
    
    return jsonify({
        'users': {
            'total': total_users,
            'active': User.query.filter_by(role='user', is_active=True).count()
        },
        'accounts': {
            'total': total_accounts,
            'total_balance': total_balance
        },
        'transactions': {
            'pending': pending_transactions,
            'approved': approved_transactions,
            'rejected': rejected_transactions
        },
        'loans': {
            'pending': pending_loans,
            'approved': approved_loans
        }
    }), 200