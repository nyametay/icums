from data import db


class DataEntry(db.Model):
    BOE_No = db.Column(db.BigInteger, primary_key=True)  # Use BigInteger for large numbers
    Customs_Office = db.Column(db.String(10), nullable=False)  # Increased length
    Declaration_Date = db.Column(db.Date, nullable=False)
    Processing_Status = db.Column(db.String(50), nullable=False)
    Due_Date = db.Column(db.Date, nullable=False)


def filter_data(custom_office=None, processing_status=None, filter_date=None):
    query = db.session.query(DataEntry)  # Start base query

    # Apply filters dynamically
    if custom_office:
        query = query.filter(DataEntry.Customs_Office == custom_office)
    if processing_status:
        query = query.filter(DataEntry.Processing_Status == processing_status)
    if filter_date:
        query = query.filter(DataEntry.Due_Date >= filter_date)

    return query
