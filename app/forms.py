from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, Optional
from app.models import User, Expense


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class ExpenseForm(FlaskForm):
    amount = FloatField('Amount (₹)', validators=[
        DataRequired(),
        NumberRange(min=0.01, message='Amount must be greater than 0')
    ])
    category = SelectField('Category', choices=[
        (cat, cat) for cat in Expense.CATEGORIES
    ], validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=200, message='Description must be less than 200 characters')
    ])
    submit = SubmitField('Save Expense')


class FilterForm(FlaskForm):
    category = SelectField('Category', choices=[
        ('', 'All Categories')
    ] + [(cat, cat) for cat in Expense.CATEGORIES])
    start_date = DateField('From', validators=[Optional()])
    end_date = DateField('To', validators=[Optional()])
    sort_by = SelectField('Sort By', choices=[
        ('date_desc', 'Date (Newest First)'),
        ('date_asc', 'Date (Oldest First)'),
        ('amount_desc', 'Amount (High to Low)'),
        ('amount_asc', 'Amount (Low to High)')
    ])
    submit = SubmitField('Apply Filters')


class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=64, message='Username must be between 3 and 64 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address')
    ])
    submit = SubmitField('Save Changes')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            if User.query.filter_by(username=username.data).first():
                raise ValidationError('Username already taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != self.original_email:
            if User.query.filter_by(email=email.data).first():
                raise ValidationError('Email already registered. Please use a different one.')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')
