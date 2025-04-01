from data import app, db
from data.models import DataEntry, filter_data
from flask import render_template, request, redirect, url_for, flash, session, Response
import pandas as pd
import io


@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
def index():
    if request.method == 'GET':
        return render_template('index.html', status='empty')


@app.route('/upload', methods=['POST'])
def upload():
    if 'excel_file' not in request.files:
        flash('File path not found', 'danger')
        return redirect(url_for('index'))

    file = request.files['excel_file']
    if file.filename == '':
        flash('File is empty', 'danger')
        return redirect(url_for('index'))

    if not file.filename.endswith(('.xlsx', '.xls')):
        flash('Excel file not found', 'danger')
        return redirect(url_for('index'))

    try:
        df = pd.read_excel(file, engine='openpyxl')  # Explicitly specify engine
    except ValueError:
        df = pd.read_excel(file, engine='xlrd')

    df = df[['BOE No.', ' Customs Office', 'Declaration Date', 'Processing Status', 'Due Date']]

    df['Declaration Date'] = pd.to_datetime(df['Declaration Date'], errors='coerce',  infer_datetime_format=True).dt.date
    df['Due Date'] = pd.to_datetime(df['Due Date'], errors='coerce',  infer_datetime_format=True).dt.date  # Convert to Date

    print(df['Processing Status'].unique())

    # Clear old data
    if db.session.query(DataEntry).count() > 0:  # Check if data exists
        db.session.query(DataEntry).delete()
        db.session.commit()

    # Insert new data
    for _, row in df.iterrows():
        entry = DataEntry(BOE_No=int(row[0]), Customs_Office=str(row[1]), Declaration_Date=row[2],  Processing_Status=str(row[3]), Due_Date=row[4])  # Adjust columns
        db.session.add(entry)
    db.session.commit()

    session['online'] = True

    flash('File uploaded and data stored successfully!', 'success')
    return redirect(url_for('table', page=1))


@app.route('/table', methods=['GET'])
def table():
    if 'online' in session:
        """Paginate data from SQLite"""
        page = request.args.get('page', 1, type=int)
        per_page = 20
        data = DataEntry.query.order_by(DataEntry.Due_Date).paginate(page=page, per_page=per_page, error_out=False)
        return render_template('table.html', data=data)
    flash('No Upload Yet', 'warning')
    return redirect(url_for('index'))


@app.route('/filter_', methods=['GET', 'POST'])
def filter_():
    if 'online' in session:
        if request.method == 'POST':
            # Get form inputs
            custom_office = request.form.get('customs_office', '').strip()
            processing_status = request.form.get('gridRadios', '').strip()
            filter_date = request.form.get('date', '').strip()

            # Convert empty strings to None
            custom_office = None if custom_office == '' else custom_office
            processing_status = None if processing_status == '' else processing_status
            filter_date = None if filter_date == '' else pd.to_datetime(filter_date, errors='coerce')
            print(custom_office, processing_status, filter_date)
            # If no filter is applied, show message & redirect
            if not any([custom_office, processing_status, filter_date]):
                flash('No Filter Was Applied', 'warning')
                return redirect(url_for('table'))

            # Redirect to GET request with filter params in the URL
            return redirect(url_for('filter_', customs_office=custom_office, processing_status=processing_status, date=filter_date))

        # GET request (for pagination)
        custom_office = request.args.get('customs_office')
        processing_status = request.args.get('processing_status')
        filter_date = request.args.get('date')

        # Convert date back to datetime
        filter_date = pd.to_datetime(filter_date, errors='coerce') if filter_date else None

        # Get filtered data as a query, not a list
        query = filter_data(custom_office, processing_status, filter_date)

        # Get pagination details
        page = request.args.get('page', 1, type=int)
        per_page = 20
        paginated_data = query.order_by(DataEntry.Due_Date).paginate(page=page, per_page=per_page, error_out=False)

        # Render table with paginated results
        return render_template('filtered_table.html', data=paginated_data, customs_office=custom_office, processing_status=processing_status, date=filter_date)
    flash('No Upload Yet', 'warning')
    return redirect(url_for('index'))


@app.route('/download')
def download():
    """Download filtered or full data as an Excel file"""
    # Get filter parameters from URL
    custom_office = request.args.get('customs_office')
    processing_status = request.args.get('processing_status')
    filter_date = request.args.get('date')

    # Convert date
    filter_date = pd.to_datetime(filter_date, errors='coerce') if filter_date else None

    # Get filtered data
    query = filter_data(custom_office, processing_status, filter_date)

    # If no filters are applied, fetch all data
    if not custom_office and not processing_status and not filter_date:
        query = DataEntry.query

    data = query.all()

    # Convert to DataFrame
    df = pd.DataFrame([{
        'BOE No': entry.BOE_No,
        'Customs Office': entry.Customs_Office,
        'Declaration Date': entry.Declaration_Date.strftime('%Y-%m-%d') if entry.Declaration_Date else '',
        'Processing Status': entry.Processing_Status,
        'Due Date': entry.Due_Date.strftime('%Y-%m-%d') if entry.Due_Date else ''
    } for entry in data])

    # Save to an in-memory buffer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    return Response(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=filtered_data.xlsx"}
    )


@app.route('/clear')
def clear():
    """Clear all stored data"""
    db.session.query(DataEntry).delete()
    db.session.commit()
    flash('Data cleared successfully.', 'success')
    return redirect(url_for('index'))
