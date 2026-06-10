from flask import Flask, render_template
from extensions import mysql, login_manager
from config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    mysql.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # User loader (import here to avoid circular imports)
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(int(user_id))

    # Register blueprints
    from routes.auth       import auth_bp
    from routes.admin      import admin_bp
    from routes.resident   import resident_bp
    from routes.security   import security_bp
    from routes.staff      import staff_bp
    from routes.accountant import accountant_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp,      url_prefix='/admin')
    app.register_blueprint(resident_bp,   url_prefix='/resident')
    app.register_blueprint(security_bp,   url_prefix='/security')
    app.register_blueprint(staff_bp,      url_prefix='/staff')
    app.register_blueprint(accountant_bp, url_prefix='/accountant')

    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
