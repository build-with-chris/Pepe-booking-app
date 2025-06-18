# auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from datamanager import DataManager
from flasgger import swag_from

auth_bp = Blueprint('auth', __name__, template_folder='templates')

dm = DataManager()

@auth_bp.route('/login', methods=['GET', 'POST'])
@swag_from('resources/swagger/auth_login.yml')
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        pw    = request.form.get('password')
        print(pw)
        artist = dm.get_artist_by_email(email)
        if artist and artist.check_password(pw):
            login_user(artist)
            flash('Welcome back!', 'success')
            return redirect(url_for('api.list_requests'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html')


# localStorage entfernen 


@auth_bp.route('/logout')
@login_required
@swag_from('resources/swagger/auth_logout.yml')

def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))