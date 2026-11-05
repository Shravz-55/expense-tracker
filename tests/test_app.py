"""
Pytest tests for the Expense Tracker application.
Run with: pytest tests/ -v
"""
import pytest
from datetime import date
from app import create_app, db
from app.models import User, Expense
from config import TestConfig


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """Create authenticated test client with a user."""
    with app.app_context():
        user = User(username='testuser', email='test@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

    client.post('/auth/login', data={
        'email': 'test@example.com',
        'password': 'password123'
    })
    return client


class TestUserRegistration:
    """Test user registration functionality."""

    def test_register_page_loads(self, client):
        """Test that registration page loads correctly."""
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b'Create Account' in response.data
        assert b'Username' in response.data
        assert b'Email' in response.data
        assert b'Password' in response.data

    def test_register_new_user(self, client, app):
        """Test successful user registration."""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'password2': 'securepass123'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Registration successful' in response.data

        with app.app_context():
            user = User.query.filter_by(email='newuser@example.com').first()
            assert user is not None
            assert user.username == 'newuser'
            assert user.check_password('securepass123')

    def test_register_duplicate_email(self, client, app):
        """Test registration fails with duplicate email."""
        with app.app_context():
            user = User(username='existing', email='existing@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()

        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'existing@example.com',
            'password': 'password123',
            'password2': 'password123'
        }, follow_redirects=True)

        assert b'Email already registered' in response.data

    def test_register_password_mismatch(self, client):
        """Test registration fails when passwords don't match."""
        response = client.post('/auth/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'password2': 'different456'
        }, follow_redirects=True)

        assert b'Passwords must match' in response.data


class TestUserLogin:
    """Test user login functionality."""

    def test_login_page_loads(self, client):
        """Test that login page loads correctly."""
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b'Login' in response.data
        assert b'Email' in response.data
        assert b'Password' in response.data

    def test_login_valid_credentials(self, client, app):
        """Test successful login with valid credentials."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()

        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Welcome' in response.data

    def test_login_invalid_password(self, client, app):
        """Test login fails with wrong password."""
        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()

        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)

        assert b'Invalid email or password' in response.data

    def test_login_nonexistent_user(self, client):
        """Test login fails for non-existent user."""
        response = client.post('/auth/login', data={
            'email': 'nobody@example.com',
            'password': 'password123'
        }, follow_redirects=True)

        assert b'Invalid email or password' in response.data

    def test_logout(self, auth_client):
        """Test user can logout."""
        response = auth_client.get('/auth/logout', follow_redirects=True)
        assert b'logged out' in response.data


class TestAddExpense:
    """Test expense creation functionality."""

    def test_add_expense_page_loads(self, auth_client):
        """Test that add expense page loads for authenticated user."""
        response = auth_client.get('/add')
        assert response.status_code == 200
        assert b'Add New Expense' in response.data
        assert b'Amount' in response.data
        assert b'Category' in response.data

    def test_add_expense_requires_login(self, client):
        """Test that add expense redirects to login for unauthenticated user."""
        response = client.get('/add', follow_redirects=True)
        assert b'Please log in' in response.data

    def test_add_expense_success(self, auth_client, app):
        """Test successful expense creation."""
        response = auth_client.post('/add', data={
            'amount': '42.50',
            'category': 'Food',
            'date': date.today().isoformat(),
            'description': 'Lunch at restaurant'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Expense added successfully' in response.data

        with app.app_context():
            expense = Expense.query.first()
            assert expense is not None
            assert expense.amount == 42.50
            assert expense.category == 'Food'
            assert expense.description == 'Lunch at restaurant'

    def test_add_expense_all_categories(self, auth_client, app):
        """Test adding expenses with all category types."""
        categories = ['Food', 'Travel', 'Bills', 'Entertainment', 'Other']

        for i, category in enumerate(categories):
            response = auth_client.post('/add', data={
                'amount': str(10.00 * (i + 1)),
                'category': category,
                'date': date.today().isoformat(),
                'description': f'Test {category}'
            }, follow_redirects=True)
            assert b'Expense added successfully' in response.data

        with app.app_context():
            assert Expense.query.count() == 5

    def test_add_expense_invalid_amount(self, auth_client):
        """Test expense creation fails with invalid amount."""
        response = auth_client.post('/add', data={
            'amount': '-10.00',
            'category': 'Food',
            'date': date.today().isoformat(),
            'description': 'Invalid'
        }, follow_redirects=True)

        assert b'Amount must be greater than 0' in response.data


class TestEditExpense:
    """Test expense editing functionality."""

    def test_edit_expense_page_loads(self, auth_client, app):
        """Test that edit expense page loads with expense data."""
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            expense = Expense(
                amount=25.00,
                category='Food',
                date=date.today(),
                description='Original description',
                user_id=user.id
            )
            db.session.add(expense)
            db.session.commit()
            expense_id = expense.id

        response = auth_client.get(f'/edit/{expense_id}')
        assert response.status_code == 200
        assert b'Edit Expense' in response.data
        assert b'25' in response.data
        assert b'Original description' in response.data

    def test_edit_expense_success(self, auth_client, app):
        """Test successful expense update."""
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            expense = Expense(
                amount=25.00,
                category='Food',
                date=date.today(),
                description='Original',
                user_id=user.id
            )
            db.session.add(expense)
            db.session.commit()
            expense_id = expense.id

        response = auth_client.post(f'/edit/{expense_id}', data={
            'amount': '50.00',
            'category': 'Travel',
            'date': date.today().isoformat(),
            'description': 'Updated description'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Expense updated successfully' in response.data

        with app.app_context():
            expense = db.session.get(Expense, expense_id)
            assert expense.amount == 50.00
            assert expense.category == 'Travel'
            assert expense.description == 'Updated description'

    def test_edit_expense_unauthorized(self, auth_client, app):
        """Test user cannot edit another user's expense."""
        with app.app_context():
            other_user = User(username='other', email='other@example.com')
            other_user.set_password('password')
            db.session.add(other_user)
            db.session.commit()

            expense = Expense(
                amount=100.00,
                category='Bills',
                date=date.today(),
                user_id=other_user.id
            )
            db.session.add(expense)
            db.session.commit()
            expense_id = expense.id

        response = auth_client.get(f'/edit/{expense_id}', follow_redirects=True)
        assert b'do not have permission' in response.data

    def test_edit_nonexistent_expense(self, auth_client):
        """Test editing non-existent expense returns 404."""
        response = auth_client.get('/edit/99999')
        assert response.status_code == 404


class TestDeleteExpense:
    """Test expense deletion functionality."""

    def test_delete_expense_success(self, auth_client, app):
        """Test successful expense deletion."""
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            expense = Expense(
                amount=25.00,
                category='Food',
                date=date.today(),
                user_id=user.id
            )
            db.session.add(expense)
            db.session.commit()
            expense_id = expense.id

        response = auth_client.post(f'/delete/{expense_id}', follow_redirects=True)

        assert response.status_code == 200
        assert b'Expense deleted successfully' in response.data

        with app.app_context():
            assert db.session.get(Expense, expense_id) is None

    def test_delete_expense_unauthorized(self, auth_client, app):
        """Test user cannot delete another user's expense."""
        with app.app_context():
            other_user = User(username='other', email='other@example.com')
            other_user.set_password('password')
            db.session.add(other_user)
            db.session.commit()

            expense = Expense(
                amount=100.00,
                category='Bills',
                date=date.today(),
                user_id=other_user.id
            )
            db.session.add(expense)
            db.session.commit()
            expense_id = expense.id

        response = auth_client.post(f'/delete/{expense_id}', follow_redirects=True)
        assert b'do not have permission' in response.data

        with app.app_context():
            assert db.session.get(Expense, expense_id) is not None

    def test_delete_requires_post(self, auth_client, app):
        """Test delete only works with POST method."""
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            expense = Expense(
                amount=25.00,
                category='Food',
                date=date.today(),
                user_id=user.id
            )
            db.session.add(expense)
            db.session.commit()
            expense_id = expense.id

        response = auth_client.get(f'/delete/{expense_id}')
        assert response.status_code == 405

    def test_delete_nonexistent_expense(self, auth_client):
        """Test deleting non-existent expense returns 404."""
        response = auth_client.post('/delete/99999')
        assert response.status_code == 404


class TestDashboard:
    """Test the dashboard summary page."""

    def test_dashboard_requires_login(self, client):
        """Test dashboard redirects to login for unauthenticated user."""
        response = client.get('/dashboard', follow_redirects=True)
        assert b'Please log in' in response.data

    def test_dashboard_shows_summary_cards(self, auth_client, app):
        """Test dashboard shows the summary cards with the right numbers."""
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            db.session.add(Expense(amount=100, category='Food', date=date.today(), user_id=user.id))
            db.session.add(Expense(amount=300, category='Travel', date=date.today(), user_id=user.id))
            db.session.commit()

        response = auth_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Total Spending' in response.data
        assert b'400.00' in response.data
        assert b'Top Category' in response.data
        assert b'Travel' in response.data

    def test_dashboard_shows_only_five_recent_expenses(self, auth_client, app):
        """Dashboard lists the 5 latest expenses, not all of them, and has no charts."""
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            for i in range(7):
                db.session.add(Expense(amount=10 + i, category='Food', date=date(2026, 1, i + 1),
                                       description=f'Item number {i}', user_id=user.id))
            db.session.commit()

        response = auth_client.get('/dashboard')
        assert b'Recent Transactions' in response.data
        assert response.data.count(b'Item number') == 5
        assert b'Item number 6' in response.data
        assert b'Item number 0' not in response.data
        assert b'monthlyChart' not in response.data

    def test_navbar_has_single_add_expense_link(self, auth_client):
        """Only the navbar should link to Add Expense."""
        response = auth_client.get('/dashboard')
        assert response.data.count(b'href="/add"') == 1

    def test_sidebar_links(self, auth_client):
        """The sidebar has all five pages."""
        response = auth_client.get('/dashboard')
        for link in (b'href="/dashboard"', b'href="/expenses"', b'href="/add"',
                     b'href="/analytics"', b'href="/auth/profile"'):
            assert link in response.data


class TestExpensesPage:
    """Test the expenses list and filtering."""

    def test_expenses_page_requires_login(self, client):
        response = client.get('/expenses', follow_redirects=True)
        assert b'Please log in' in response.data

    def test_expenses_page_shows_expenses(self, auth_client, app):
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            db.session.add(Expense(amount=99.99, category='Entertainment', date=date.today(),
                                   description='Concert tickets', user_id=user.id))
            db.session.commit()

        response = auth_client.get('/expenses')
        assert response.status_code == 200
        assert b'99.99' in response.data
        assert b'Entertainment' in response.data
        assert b'Concert tickets' in response.data

    def test_expenses_filter_by_category(self, auth_client, app):
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            db.session.add(Expense(amount=50, category='Food', date=date.today(), description='Food item', user_id=user.id))
            db.session.add(Expense(amount=100, category='Bills', date=date.today(), description='Bills item', user_id=user.id))
            db.session.commit()

        response = auth_client.get('/expenses?category=Food')
        assert b'Food item' in response.data
        assert b'Bills item' not in response.data


class TestAnalytics:
    """Test the analytics page."""

    def test_analytics_requires_login(self, client):
        response = client.get('/analytics', follow_redirects=True)
        assert b'Please log in' in response.data

    def test_analytics_shows_charts(self, auth_client, app):
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            db.session.add(Expense(amount=100, category='Food', date=date.today(), user_id=user.id))
            db.session.commit()

        response = auth_client.get('/analytics')
        assert response.status_code == 200
        assert b'Monthly Spending Trend' in response.data
        assert b'By Category' in response.data
        assert b'Category Breakdown' in response.data

    def test_analytics_empty_state(self, auth_client):
        response = auth_client.get('/analytics')
        assert response.status_code == 200
        assert b'No expenses yet' in response.data


class TestProfile:
    """Test the profile and change-password pages."""

    def test_profile_requires_login(self, client):
        response = client.get('/auth/profile', follow_redirects=True)
        assert b'Please log in' in response.data

    def test_profile_page_loads(self, auth_client):
        response = auth_client.get('/auth/profile')
        assert response.status_code == 200
        assert b'testuser' in response.data
        assert b'test@example.com' in response.data
        assert b'Change Password' in response.data

    def test_update_profile(self, auth_client, app):
        response = auth_client.post('/auth/profile', data={
            'username': 'newname',
            'email': 'new@example.com'
        }, follow_redirects=True)
        assert b'Profile updated successfully' in response.data
        with app.app_context():
            user = User.query.filter_by(email='new@example.com').first()
            assert user is not None
            assert user.username == 'newname'

    def test_update_profile_duplicate_username(self, auth_client, app):
        with app.app_context():
            other = User(username='taken', email='other@example.com')
            other.set_password('password123')
            db.session.add(other)
            db.session.commit()

        response = auth_client.post('/auth/profile', data={
            'username': 'taken',
            'email': 'test@example.com'
        }, follow_redirects=True)
        assert b'Username already taken' in response.data

    def test_change_password_success(self, auth_client, app):
        response = auth_client.post('/auth/change-password', data={
            'current_password': 'password123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        }, follow_redirects=True)
        assert b'Password changed successfully' in response.data
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            assert user.check_password('newpass456')
            assert not user.check_password('password123')

    def test_change_password_wrong_current(self, auth_client, app):
        response = auth_client.post('/auth/change-password', data={
            'current_password': 'wrongpass',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456'
        }, follow_redirects=True)
        assert b'Current password is incorrect' in response.data
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            assert user.check_password('password123')

    def test_change_password_mismatch(self, auth_client):
        response = auth_client.post('/auth/change-password', data={
            'current_password': 'password123',
            'new_password': 'newpass456',
            'confirm_password': 'different789'
        }, follow_redirects=True)
        assert b'Passwords must match' in response.data
