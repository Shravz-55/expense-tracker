from flask import render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from collections import defaultdict
from sqlalchemy import func, extract
from app import db
from app.expenses import bp
from app.models import Expense
from app.forms import ExpenseForm, FilterForm


@bp.route('/dashboard')
@login_required
def dashboard():
    form = FilterForm()
    query = Expense.query.filter_by(user_id=current_user.id)

    # Apply filters
    category = request.args.get('category', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    sort_by = request.args.get('sort_by', 'date_desc')

    if category:
        query = query.filter_by(category=category)
        form.category.data = category

    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Expense.date >= start)
            form.start_date.data = start
        except ValueError:
            pass

    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Expense.date <= end)
            form.end_date.data = end
        except ValueError:
            pass

    # Apply sorting
    form.sort_by.data = sort_by
    if sort_by == 'date_desc':
        query = query.order_by(Expense.date.desc())
    elif sort_by == 'date_asc':
        query = query.order_by(Expense.date.asc())
    elif sort_by == 'amount_desc':
        query = query.order_by(Expense.amount.desc())
    elif sort_by == 'amount_asc':
        query = query.order_by(Expense.amount.asc())

    expenses = query.all()

    # Calculate totals for display
    total_spending = sum(e.amount for e in expenses)

    # Get analytics data (unfiltered for charts)
    analytics = get_analytics_data(current_user.id)

    return render_template('expenses/dashboard.html',
                           title='Dashboard',
                           expenses=expenses,
                           form=form,
                           total_spending=total_spending,
                           categories=Expense.CATEGORIES,
                           analytics=analytics)


def get_analytics_data(user_id):
    """Calculate analytics for charts and summary cards."""
    try:
        all_expenses = Expense.query.filter_by(user_id=user_id).all()

        if not all_expenses:
            return {
                'total': 0,
                'count': 0,
                'category_totals': {},
                'monthly_totals': {},
                'avg_expense': 0,
                'this_month': 0
            }

        # Total spending
        total = sum(e.amount for e in all_expenses)

        # Category-wise totals
        category_totals = defaultdict(float)
        for expense in all_expenses:
            category_totals[expense.category] += expense.amount

        # Monthly totals (last 12 months)
        monthly_totals = defaultdict(float)
        for expense in all_expenses:
            month_key = expense.date.strftime('%Y-%m')
            monthly_totals[month_key] += expense.amount

        # Sort monthly totals by date
        sorted_months = sorted(monthly_totals.items())[-12:]
        monthly_totals = dict(sorted_months)

        # Average expense
        avg_expense = total / len(all_expenses) if all_expenses else 0

        # This month's spending
        today = date.today()
        this_month_key = today.strftime('%Y-%m')
        this_month_total = monthly_totals.get(this_month_key, 0)

        return {
            'total': round(total, 2),
            'count': len(all_expenses),
            'category_totals': dict(category_totals),
            'monthly_totals': monthly_totals,
            'avg_expense': round(avg_expense, 2),
            'this_month': round(this_month_total, 2)
        }
    except Exception:
        return {
            'total': 0,
            'count': 0,
            'category_totals': {},
            'monthly_totals': {},
            'avg_expense': 0,
            'this_month': 0
        }


@bp.route('/api/analytics')
@login_required
def api_analytics():
    """JSON endpoint for chart data."""
    try:
        analytics = get_analytics_data(current_user.id)
        return jsonify(analytics)
    except Exception:
        return jsonify({'error': 'Failed to load analytics'}), 500


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    form = ExpenseForm()
    if form.validate_on_submit():
        try:
            expense = Expense(
                amount=form.amount.data,
                category=form.category.data,
                date=form.date.data,
                description=form.description.data,
                user_id=current_user.id
            )
            db.session.add(expense)
            db.session.commit()
            flash('Expense added successfully!', 'success')
            return redirect(url_for('expenses.dashboard'))
        except Exception:
            db.session.rollback()
            flash('An error occurred while adding the expense. Please try again.', 'danger')

    # Default date to today
    if not form.date.data:
        form.date.data = date.today()

    return render_template('expenses/add.html', title='Add Expense', form=form)


@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_expense(id):
    expense = db.session.get(Expense, id)
    if expense is None:
        abort(404)

    # Ensure user owns this expense
    if expense.user_id != current_user.id:
        flash('You do not have permission to edit this expense.', 'danger')
        return redirect(url_for('expenses.dashboard'))

    form = ExpenseForm(obj=expense)
    if form.validate_on_submit():
        try:
            expense.amount = form.amount.data
            expense.category = form.category.data
            expense.date = form.date.data
            expense.description = form.description.data
            db.session.commit()
            flash('Expense updated successfully!', 'success')
            return redirect(url_for('expenses.dashboard'))
        except Exception:
            db.session.rollback()
            flash('An error occurred while updating the expense. Please try again.', 'danger')

    return render_template('expenses/edit.html', title='Edit Expense', form=form, expense=expense)


@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_expense(id):
    expense = db.session.get(Expense, id)
    if expense is None:
        abort(404)

    # Ensure user owns this expense
    if expense.user_id != current_user.id:
        flash('You do not have permission to delete this expense.', 'danger')
        return redirect(url_for('expenses.dashboard'))

    try:
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted successfully!', 'success')
    except Exception:
        db.session.rollback()
        flash('An error occurred while deleting the expense. Please try again.', 'danger')

    return redirect(url_for('expenses.dashboard'))
