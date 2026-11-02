from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.models import User
from app.forms import LoginForm, RegistrationForm


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('expenses.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')

    return render_template('auth/register.html', title='Register', form=form)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('expenses.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.query.filter_by(email=form.email.data).first()
            if user is None or not user.check_password(form.password.data):
                flash('Invalid email or password.', 'danger')
                return redirect(url_for('auth.login'))

            login_user(user)
            flash(f'Welcome back, {user.username}!', 'success')

            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('expenses.dashboard')
            return redirect(next_page)
        except Exception as e:
            flash('An error occurred during login. Please try again.', 'danger')

    return render_template('auth/login.html', title='Login', form=form)


@bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
