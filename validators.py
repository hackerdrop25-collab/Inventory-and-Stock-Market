import re

# Optional email validator - fallback to simple regex if not available
try:
    from email_validator import validate_email, EmailNotValidError
    HAS_EMAIL_VALIDATOR = True
except ImportError:
    HAS_EMAIL_VALIDATOR = False
    EmailNotValidError = None

def validate_email_address(email):
    """Validate email address format"""
    if HAS_EMAIL_VALIDATOR:
        try:
            valid = validate_email(email)
            return True, valid.email
        except EmailNotValidError as e:
            return False, str(e)
    else:
        # Fallback to simple regex validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return True, email
        return False, "Invalid email format"

def validate_password(password):
    """
    Validate password strength.
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    if errors:
        return False, errors
    
    return True, []

def validate_product_input(name, category, price, quantity, supplier):
    """Validate product form input"""
    errors = []
    
    if not name or len(name.strip()) < 2:
        errors.append("Product name must be at least 2 characters")
    
    if not category or len(category.strip()) < 2:
        errors.append("Category must be at least 2 characters")
    
    try:
        price_float = float(price)
        if price_float < 0:
            errors.append("Price cannot be negative")
    except ValueError:
        errors.append("Price must be a valid number")
    
    try:
        quantity_int = int(quantity)
        if quantity_int < 0:
            errors.append("Quantity cannot be negative")
    except ValueError:
        errors.append("Quantity must be a valid integer")
    
    if not supplier or len(supplier.strip()) < 2:
        errors.append("Supplier must be at least 2 characters")
    
    return len(errors) == 0, errors

def validate_sale_input(quantity, customer_name):
    """Validate sale form input"""
    errors = []
    
    try:
        quantity_int = int(quantity)
        if quantity_int <= 0:
            errors.append("Quantity must be greater than 0")
    except ValueError:
        errors.append("Quantity must be a valid integer")
    
    if customer_name and len(customer_name.strip()) > 100:
        errors.append("Customer name too long")
    
    return len(errors) == 0, errors

def validate_supplier_input(name, contact, email, address):
    """Validate supplier form input"""
    errors = []
    
    if not name or len(name.strip()) < 2:
        errors.append("Supplier name must be at least 2 characters")
    
    if not contact or len(contact.strip()) < 5:
        errors.append("Contact must be at least 5 characters")
    
    is_valid, msg = validate_email_address(email)
    if not is_valid:
        errors.append(f"Invalid email: {msg}")
    
    if not address or len(address.strip()) < 5:
        errors.append("Address must be at least 5 characters")
    
    return len(errors) == 0, errors

def validate_return_input(quantity, reason):
    """Validate return form input"""
    errors = []
    
    try:
        quantity_int = int(quantity)
        if quantity_int <= 0:
            errors.append("Quantity must be greater than 0")
    except ValueError:
        errors.append("Quantity must be a valid integer")
    
    if not reason or len(reason.strip()) < 3:
        errors.append("Return reason must be at least 3 characters")
    
    return len(errors) == 0, errors
