from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Decimal(10,2), nullable=False)
    image_url = db.Column(db.String(255))
    category = db.Column(db.String(50))
    stock = db.Column(db.Integer, default=0)
    featured = db.Column(db.Boolean, default=False)
    status = db.Column(db.Enum('active', 'inactive', 'out_of_stock'), default='active')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp()) 