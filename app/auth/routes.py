from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.auth import bp
from app.models import User
from app.forms import LoginForm, RegistrationForm, ProfileForm, ChangePasswordForm


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


def _render_profile(profile_form, password_form):
    return render_template('auth/profile.html', title='My Profile',
                           form=profile_form, pw_form=password_form,
                           expense_count=current_user.expenses.count())


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(current_user.username, current_user.email,
                       obj=current_user if request.method == 'GET' else None)
    if form.validate_on_submit():
        try:
            current_user.username = form.username.data
            current_user.email = form.email.data
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
        except Exception:
            db.session.rollback()
            flash('An error occurred while updating your profile. Please try again.', 'danger')

    return _render_profile(form, ChangePasswordForm())


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            form.current_password.errors.append('Current password is incorrect.')
        else:
            try:
                current_user.set_password(form.new_password.data)
                db.session.commit()
                flash('Password changed successfully!', 'success')
                return redirect(url_for('auth.profile'))
            except Exception:
                db.session.rollback()
                flash('An error occurred while changing your password. Please try again.', 'danger')

    profile_form = ProfileForm(current_user.username, current_user.email, obj=current_user)
    return _render_profile(profile_form, form)
