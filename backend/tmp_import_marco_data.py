import json
import mimetypes
import os
import urllib.request
import urllib.parse
import uuid

BASE = 'http://127.0.0.1:8001/api/v1'
EMAIL = 'demo-admin@example.com'
PASSWORD = 'DemoPass123!'


def request_json(method, path, token=None, payload=None, params=None):
    url = BASE + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        if clean:
            url += '?' + urllib.parse.urlencode(clean)
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode('utf-8')
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        raise RuntimeError(f'{method} {path} failed: {exc.code} {detail}')


def request_multipart(path, token, fields, file_field, file_path):
    boundary = '----WebKitFormBoundary' + uuid.uuid4().hex
    body = bytearray()
    for key, value in fields.items():
        body.extend(f'--{boundary}\r\n'.encode())
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        body.extend(str(value).encode('utf-8'))
        body.extend(b'\r\n')
    filename = os.path.basename(file_path)
    mime = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
    with open(file_path, 'rb') as handle:
        file_bytes = handle.read()
    body.extend(f'--{boundary}\r\n'.encode())
    body.extend(f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode())
    body.extend(f'Content-Type: {mime}\r\n\r\n'.encode())
    body.extend(file_bytes)
    body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode())
    req = urllib.request.Request(
        BASE + path,
        data=bytes(body),
        method='POST',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': f'multipart/form-data; boundary={boundary}',
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        raise RuntimeError(f'POST {path} upload failed: {exc.code} {detail}')


def list_all(path, token, params=None):
    data = request_json('GET', path, token=token, params={**(params or {}), 'limit': 500})
    return data.get('items', [])


def post(path, token, payload):
    return request_json('POST', path, token=token, payload=payload)


def find_by(rows, key, value):
    for row in rows:
        if str(row.get(key, '')).strip().lower() == str(value).strip().lower():
            return row
    return None


def ensure_vendor(token, cache, *, name, vendor_type='contractor', company_id=1, **extra):
    existing = find_by(cache['vendors'], 'name', name)
    if existing:
        return existing
    payload = {'name': name, 'vendor_type': vendor_type, 'company_id': company_id}
    payload.update(extra)
    created = post('/vendors/', token, payload)
    cache['vendors'].append(created)
    return created


def ensure_contract(token, cache, *, contract_no, project_id, vendor_id, title, **extra):
    existing = find_by(cache['contracts'], 'contract_no', contract_no)
    if existing:
        return existing
    payload = {'project_id': project_id, 'vendor_id': vendor_id, 'contract_no': contract_no, 'title': title}
    payload.update(extra)
    created = post('/contracts/', token, payload)
    cache['contracts'].append(created)
    return created


def ensure_project(token, cache, *, company_id, name, code=None, **extra):
    for row in cache['projects']:
        if row['company_id'] == company_id and row['name'].strip().lower() == name.strip().lower():
            return row
        if code and row.get('code') == code:
            return row
    payload = {'company_id': company_id, 'name': name, 'code': code}
    payload.update(extra)
    created = post('/projects/', token, payload)
    cache['projects'].append(created)
    return created


def ensure_labour_contractor(token, cache, *, contractor_name, company_id=1, **extra):
    existing = find_by(cache['labour_contractors'], 'contractor_name', contractor_name)
    if existing:
        return existing
    payload = {'contractor_name': contractor_name, 'company_id': company_id}
    payload.update(extra)
    created = post('/labour-contractors/', token, payload)
    cache['labour_contractors'].append(created)
    return created


def ensure_labour(token, cache, *, full_name, labour_code, company_id=1, daily_rate=0, unit='day', **extra):
    existing = find_by(cache['labours'], 'full_name', full_name)
    if existing:
        return existing
    payload = {'company_id': company_id, 'labour_code': labour_code, 'full_name': full_name, 'daily_rate': daily_rate, 'unit': unit}
    payload.update(extra)
    created = post('/labours/', token, payload)
    cache['labours'].append(created)
    return created


def ensure_attendance(token, cache, *, muster_no, payload):
    existing = find_by(cache['labour_attendance'], 'muster_no', muster_no)
    if existing:
        return existing
    created = post('/labour-attendance/', token, payload)
    cache['labour_attendance'].append(created)
    return created


def transition_attendance(token, attendance, target_status):
    order = {'draft': 0, 'submitted': 1, 'approved': 2}
    if order.get(attendance['status'], -1) >= order.get(target_status, -1):
        return attendance
    action = '/submit' if target_status == 'submitted' else '/approve'
    updated = post(f"/labour-attendance/{attendance['id']}{action}", token, {'remarks': f'Compiled from source sheet to reach {target_status}'})
    attendance.update(updated)
    return attendance


def ensure_labour_bill(token, cache, *, bill_no, payload):
    existing = find_by(cache['labour_bills'], 'bill_no', bill_no)
    if existing:
        return existing
    created = post('/labour-bills/', token, payload)
    cache['labour_bills'].append(created)
    return created


def transition_labour_bill(token, bill, target_status):
    order = {'draft': 0, 'submitted': 1, 'approved': 2, 'paid': 3}
    if order.get(bill['status'], -1) >= order.get(target_status, -1):
        return bill
    action = '/approve' if target_status == 'approved' else '/mark-paid'
    updated = post(f"/labour-bills/{bill['id']}{action}", token, {'remarks': f'Status moved to {target_status}'})
    bill.update(updated)
    return bill


def ensure_labour_advance(token, cache, *, advance_no, payload):
    existing = find_by(cache['labour_advances'], 'advance_no', advance_no)
    if existing:
        return existing
    created = post('/labour-advances/', token, payload)
    cache['labour_advances'].append(created)
    return created


def ensure_payment(token, cache, *, contract_id, payment_date, amount, remarks, payment_mode='manual', reference_no=None):
    for row in cache['payments']:
        if row['contract_id'] == contract_id and row['payment_date'] == payment_date and abs(float(row['amount']) - float(amount)) < 0.01 and (row.get('remarks') or '') == remarks:
            return row
    payload = {'contract_id': contract_id, 'payment_date': payment_date, 'amount': amount, 'payment_mode': payment_mode, 'reference_no': reference_no, 'remarks': remarks}
    created = post('/payments/', token, payload)
    cache['payments'].append(created)
    return created


def transition_payment(token, payment, target_status):
    order = {'draft': 0, 'approved': 1, 'released': 2}
    if order.get(payment['status'], -1) >= order.get(target_status, -1):
        return payment
    action = '/approve' if target_status == 'approved' else '/release'
    updated = post(f"/payments/{payment['id']}{action}", token, {'remarks': f'Status moved to {target_status}'})
    payment.update(updated)
    return payment


def ensure_boq_item(token, contract_id, cache, *, description, unit, quantity, rate, amount, item_code=None, category=None):
    key = (contract_id, description.strip().lower())
    if key in cache['boq_items']:
        return cache['boq_items'][key]
    items = list_all(f'/contracts/{contract_id}/boq-items/', token)
    for item in items:
        if item['description'].strip().lower() == description.strip().lower():
            cache['boq_items'][key] = item
            return item
    created = post(f'/contracts/{contract_id}/boq-items/', token, {'item_code': item_code, 'description': description, 'unit': unit, 'quantity': quantity, 'rate': rate, 'amount': amount, 'category': category})
    cache['boq_items'][key] = created
    return created


def ensure_measurement(token, cache, *, measurement_no, payload):
    existing = find_by(cache['measurements'], 'measurement_no', measurement_no)
    if existing:
        return existing
    created = post('/measurements/', token, payload)
    cache['measurements'].append(created)
    return created


def transition_measurement(token, measurement, target_status):
    order = {'draft': 0, 'submitted': 1, 'approved': 2}
    if order.get(measurement['status'], -1) >= order.get(target_status, -1):
        return measurement
    action = '/submit' if target_status == 'submitted' else '/approve'
    updated = post(f"/measurements/{measurement['id']}{action}", token, {})
    measurement.update(updated)
    return measurement


def ensure_ra_bill(token, cache, *, contract_id, bill_no, bill_date, period_from, period_to, remarks, deductions):
    for row in cache['ra_bills']:
        if row['contract_id'] == contract_id and int(row['bill_no']) == int(bill_no):
            return row
    created = post('/ra-bills/', token, {'contract_id': contract_id, 'bill_no': int(bill_no), 'bill_date': bill_date, 'period_from': period_from, 'period_to': period_to, 'remarks': remarks, 'deductions': deductions})
    cache['ra_bills'].append(created)
    return created


def generate_ra_bill(token, bill, payload):
    updated = post(f"/ra-bills/{bill['id']}/generate", token, payload)
    bill.update(updated)
    return bill


def transition_ra_bill(token, bill, target_status):
    order = {'draft': 0, 'submitted': 1, 'verified': 2, 'approved': 3, 'partially_paid': 4, 'paid': 5}
    if order.get(bill['status'], -1) >= order.get(target_status, -1):
        return bill
    action_map = {'submitted': '/submit', 'verified': '/verify', 'approved': '/approve'}
    updated = post(f"/ra-bills/{bill['id']}{action_map[target_status]}", token, {'remarks': f'Status moved to {target_status}'})
    bill.update(updated)
    return bill


def ensure_document(token, cache, *, title, entity_type, entity_id, document_type, remarks, file_path):
    for doc in cache['documents']:
        if doc['title'] == title and doc['entity_type'] == entity_type and int(doc['entity_id']) == int(entity_id):
            return doc
    created = request_multipart('/documents/upload', token, {'entity_type': entity_type, 'entity_id': entity_id, 'title': title, 'document_type': document_type, 'remarks': remarks}, 'file', file_path)
    cache['documents'].append(created)
    return created


def main():
    login = request_json('POST', '/auth/login', payload={'email': EMAIL, 'password': PASSWORD})
    token = login['access_token']

    cache = {
        'vendors': list_all('/vendors/', token),
        'contracts': list_all('/contracts/', token),
        'projects': list_all('/projects/', token),
        'labour_contractors': list_all('/labour-contractors/', token),
        'labours': list_all('/labours/', token),
        'labour_attendance': list_all('/labour-attendance/', token),
        'labour_bills': list_all('/labour-bills/', token),
        'labour_advances': list_all('/labour-advances/', token),
        'payments': list_all('/payments/', token),
        'measurements': list_all('/measurements/', token),
        'ra_bills': list_all('/ra-bills/', token),
        'documents': list_all('/documents/', token),
        'boq_items': {},
    }
    companies = list_all('/companies/', token)
    company = next(c for c in companies if c['name'] == 'Marco Enterpricess')
    company_id = company['id']
    project = ensure_project(token, cache, company_id=company_id, name='Omaxe Ananda Tower-E Prayagraj', code='OMAXE-ATE-001', description='Marco source data filing target project.', client_name='Omaxe', location='Naini, Prayagraj', status='active')
    project_id = project['id']

    roshni = ensure_vendor(token, cache, name='Roshni Enterprises', vendor_type='supplier', company_id=company_id, gst_number='09PFPK6068B1ZW', phone='9839047835', address='Flat No.-433/2, Chak Babura, Dadri Taluka, Naini, Prayagraj')
    anshu_vendor = ensure_vendor(token, cache, name='Anshu Electrical', vendor_type='contractor', company_id=company_id)
    uma_vendor = ensure_vendor(token, cache, name='Uma Shankar', vendor_type='contractor', company_id=company_id)
    samarjeet_vendor = ensure_vendor(token, cache, name='Samarjeet', vendor_type='contractor', company_id=company_id)
    ganesh_vendor = ensure_vendor(token, cache, name='Ganesh', vendor_type='contractor', company_id=company_id)

    anshu_contract = ensure_contract(token, cache, contract_no='ANSHU-ELE-001', project_id=project_id, vendor_id=anshu_vendor['id'], title='Electrical Work - Shiva + Tower-E LIG/EWS', scope_of_work='Electrical work', status='active')
    uma_contract = ensure_contract(token, cache, contract_no='UMA-GLZ-001', project_id=project_id, vendor_id=uma_vendor['id'], title='Aluminium Framing & Glazing Work - Shiva Phase-2', scope_of_work='Aluminium framing, glazing, shutter cutting, hardware fixing, handing-over', start_date='2025-12-24', end_date='2026-01-15', original_value=437444.97, revised_value=437444.97, retention_percentage=5, status='active')
    samarjeet_contract = ensure_contract(token, cache, contract_no='SAM-BRK-001', project_id=project_id, vendor_id=samarjeet_vendor['id'], title='Brickwork', scope_of_work='Brickwork', status='active')
    ganesh_contract = ensure_contract(token, cache, contract_no='GAN-SHT-001', project_id=project_id, vendor_id=ganesh_vendor['id'], title='Shuttering', scope_of_work='Shuttering', status='active')

    boq_rows = [
        ('GLZ-01', 'Installation of aluminium framing & glazing work of door & window outer framing cutting, making & fixing work', 'SFT', 12763.44, 12.0, 153161.34),
        ('GLZ-02', 'Shutter cutting, making & fixing work', 'SFT', 13898.06, 12.0, 166776.75),
        ('GLZ-03', 'Hardware & glazing fixing work', 'SFT', 9792.24, 12.0, 117506.88),
        ('GLZ-04', 'Handing-over', 'SFT', 0.0, 4.0, 0.0),
    ]
    boq_items = {}
    for code, desc, unit, qty, rate, amt in boq_rows:
        boq_items[code] = ensure_boq_item(token, uma_contract['id'], cache, item_code=code, description=desc, unit=unit, quantity=qty, rate=rate, amount=amt, category='Glazing')

    measurement = ensure_measurement(token, cache, measurement_no='MEA-UMA-2026-01-20', payload={'contract_id': uma_contract['id'], 'measurement_no': 'MEA-UMA-2026-01-20', 'measurement_date': '2026-01-20', 'remarks': 'Filed from the 3rd RA bill sheet image for Uma Shankar.', 'items': [
        {'boq_item_id': boq_items['GLZ-01']['id'], 'current_quantity': 1021.08, 'rate': 12.0, 'remarks': 'This bill qty from 3rd RA sheet'},
        {'boq_item_id': boq_items['GLZ-02']['id'], 'current_quantity': 1832.89, 'rate': 12.0, 'remarks': 'This bill qty from 3rd RA sheet'},
        {'boq_item_id': boq_items['GLZ-03']['id'], 'current_quantity': 2644.71, 'rate': 12.0, 'remarks': 'This bill qty from 3rd RA sheet'},
    ]})
    measurement = transition_measurement(token, measurement, 'submitted')
    measurement = transition_measurement(token, measurement, 'approved')

    ra_bill = ensure_ra_bill(token, cache, contract_id=uma_contract['id'], bill_no=3, bill_date='2026-01-20', period_from='2025-12-24', period_to='2026-01-15', remarks='3rd RA bill filed from source image.', deductions=[
        {'deduction_type': 'tds', 'description': 'TDS @ 1%', 'percentage': 1},
        {'deduction_type': 'retention', 'description': 'Retention @ 5%', 'percentage': 5},
        {'deduction_type': 'advance', 'description': 'Advance paid payment', 'amount': 10000},
    ])
    ra_bill = generate_ra_bill(token, ra_bill, {'apply_contract_retention': False, 'deductions': [
        {'deduction_type': 'tds', 'description': 'TDS @ 1%', 'percentage': 1},
        {'deduction_type': 'retention', 'description': 'Retention @ 5%', 'percentage': 5},
        {'deduction_type': 'advance', 'description': 'Advance paid payment', 'amount': 10000},
    ]})
    ra_bill = transition_ra_bill(token, ra_bill, 'submitted')
    ra_bill = transition_ra_bill(token, ra_bill, 'verified')
    ra_bill = transition_ra_bill(token, ra_bill, 'approved')

    contractor_names = ['Departmental LBR', 'Samarjeet', 'Bihari', 'Rajender', 'Chhatrapal', 'Arvind Painter', 'Khokan', 'Afsar', 'Khurshid', 'VK Enterprises', 'Giasiram', 'Salman', 'Monu', 'Ganesh', 'Departmental', 'Umasankar', 'Anshu', 'Aslam', 'Akram', 'Mehanawaz']
    contractors = {}
    for idx, name in enumerate(contractor_names, start=1):
        contractors[name] = ensure_labour_contractor(token, cache, contractor_name=name, company_id=company_id, contractor_code=f'LC-{idx:03d}', is_active=True)
    dept_contractor = contractors['Departmental LBR']

    labour_rows = [('LAB-001', 'Ramjivan', 'Mason', 600), ('LAB-002', 'Sangesh', 'Mason', 600), ('LAB-003', 'Kadir', 'Mason', 600), ('LAB-004', 'Parmod', 'Mason', 600), ('LAB-005', 'Hussain', 'Beldar', 400), ('LAB-006', 'Acchelal', 'Beldar', 400), ('LAB-007', 'Aasmani', 'Cooli', 350), ('LAB-008', 'Madeena', 'Cooli', 350), ('LAB-009', 'Haseena', 'Cooli', 350), ('LAB-010', 'Sitra', 'Cooli', 350), ('LAB-011', 'Geeta', 'Cooli', 350), ('LAB-012', 'Kusum', 'Cooli', 350), ('LAB-013', 'Munna Devi', 'Cooli', 350), ('LAB-014', 'Shyam Sundri', 'Cooli', 350), ('LAB-015', 'Pratima', 'Cooli', 350), ('LAB-016', 'Pooja', 'Cooli', 350)]
    labour_map = {}
    for code, name, trade, rate in labour_rows:
        labour_map[name] = ensure_labour(token, cache, full_name=name, labour_code=code, company_id=company_id, trade=trade, daily_rate=rate, contractor_id=dept_contractor['id'], is_active=True)

    jan_attendance = ensure_attendance(token, cache, muster_no='DEPTL-JAN-26', payload={'muster_no': 'DEPTL-JAN-26', 'project_id': project_id, 'contractor_id': dept_contractor['id'], 'date': '2026-01-31', 'status': 'draft', 'remarks': 'Compiled monthly attendance from January 2026 departmental labour sheet.', 'items': [
        {'labour_id': labour_map['Ramjivan']['id'], 'attendance_status': 'present', 'present_days': 33.75, 'wage_rate': 600},
        {'labour_id': labour_map['Sangesh']['id'], 'attendance_status': 'present', 'present_days': 6.38, 'wage_rate': 600},
        {'labour_id': labour_map['Hussain']['id'], 'attendance_status': 'present', 'present_days': 15.63, 'wage_rate': 400},
        {'labour_id': labour_map['Acchelal']['id'], 'attendance_status': 'present', 'present_days': 6.63, 'wage_rate': 400},
        {'labour_id': labour_map['Aasmani']['id'], 'attendance_status': 'present', 'present_days': 17.38, 'wage_rate': 350},
        {'labour_id': labour_map['Madeena']['id'], 'attendance_status': 'present', 'present_days': 21.13, 'wage_rate': 350},
        {'labour_id': labour_map['Haseena']['id'], 'attendance_status': 'present', 'present_days': 24.88, 'wage_rate': 350},
        {'labour_id': labour_map['Sitra']['id'], 'attendance_status': 'present', 'present_days': 20.25, 'wage_rate': 350},
        {'labour_id': labour_map['Geeta']['id'], 'attendance_status': 'present', 'present_days': 24.38, 'wage_rate': 350},
        {'labour_id': labour_map['Kusum']['id'], 'attendance_status': 'present', 'present_days': 22.00, 'wage_rate': 350},
        {'labour_id': labour_map['Munna Devi']['id'], 'attendance_status': 'present', 'present_days': 18.50, 'wage_rate': 350},
        {'labour_id': labour_map['Shyam Sundri']['id'], 'attendance_status': 'present', 'present_days': 27.00, 'wage_rate': 350},
        {'labour_id': labour_map['Pratima']['id'], 'attendance_status': 'present', 'present_days': 6.50, 'wage_rate': 350},
    ]})
    jan_attendance = transition_attendance(token, jan_attendance, 'submitted')
    jan_attendance = transition_attendance(token, jan_attendance, 'approved')

    feb_attendance = ensure_attendance(token, cache, muster_no='DEPTL-FEB-26', payload={'muster_no': 'DEPTL-FEB-26', 'project_id': project_id, 'contractor_id': dept_contractor['id'], 'date': '2026-02-28', 'status': 'draft', 'remarks': 'Compiled monthly attendance from February 2026 departmental labour sheet.', 'items': [
        {'labour_id': labour_map['Ramjivan']['id'], 'attendance_status': 'present', 'present_days': 33.50, 'wage_rate': 600},
        {'labour_id': labour_map['Sangesh']['id'], 'attendance_status': 'present', 'present_days': 9.13, 'wage_rate': 600},
        {'labour_id': labour_map['Kadir']['id'], 'attendance_status': 'present', 'present_days': 15.00, 'wage_rate': 600},
        {'labour_id': labour_map['Parmod']['id'], 'attendance_status': 'present', 'present_days': 3.00, 'wage_rate': 600},
        {'labour_id': labour_map['Acchelal']['id'], 'attendance_status': 'present', 'present_days': 8.88, 'wage_rate': 400},
        {'labour_id': labour_map['Madeena']['id'], 'attendance_status': 'present', 'present_days': 16.25, 'wage_rate': 350},
        {'labour_id': labour_map['Haseena']['id'], 'attendance_status': 'present', 'present_days': 15.88, 'wage_rate': 350},
        {'labour_id': labour_map['Sitra']['id'], 'attendance_status': 'present', 'present_days': 14.63, 'wage_rate': 350},
        {'labour_id': labour_map['Geeta']['id'], 'attendance_status': 'present', 'present_days': 25.50, 'wage_rate': 350},
        {'labour_id': labour_map['Kusum']['id'], 'attendance_status': 'present', 'present_days': 28.00, 'wage_rate': 350},
        {'labour_id': labour_map['Munna Devi']['id'], 'attendance_status': 'present', 'present_days': 20.00, 'wage_rate': 350},
        {'labour_id': labour_map['Shyam Sundri']['id'], 'attendance_status': 'present', 'present_days': 27.88, 'wage_rate': 350},
        {'labour_id': labour_map['Pratima']['id'], 'attendance_status': 'present', 'present_days': 7.88, 'wage_rate': 350},
        {'labour_id': labour_map['Pooja']['id'], 'attendance_status': 'present', 'present_days': 3.00, 'wage_rate': 350},
    ]})
    feb_attendance = transition_attendance(token, feb_attendance, 'submitted')
    feb_attendance = transition_attendance(token, feb_attendance, 'approved')

    jan_bill = ensure_labour_bill(token, cache, bill_no='45TH-RA-JAN-26', payload={'bill_no': '45TH-RA-JAN-26', 'project_id': project_id, 'contractor_id': dept_contractor['id'], 'period_start': '2026-01-01', 'period_end': '2026-01-31', 'status': 'submitted', 'deductions': 42500, 'remarks': 'January departmental labour bill. Receiver amount 23000 and balance amount 31175 captured from source sheet.', 'attendance_ids': [jan_attendance['id']]})
    jan_bill = transition_labour_bill(token, jan_bill, 'approved')
    feb_bill = ensure_labour_bill(token, cache, bill_no='46TH-RA-FEB-26', payload={'bill_no': '46TH-RA-FEB-26', 'project_id': project_id, 'contractor_id': dept_contractor['id'], 'period_start': '2026-02-01', 'period_end': '2026-02-28', 'status': 'submitted', 'deductions': 55494, 'remarks': 'February departmental labour bill. Weekly advance 48500 and Jan negative 6994 combined to reach balance paid amount 40081 from source sheet.', 'attendance_ids': [feb_attendance['id']]})
    feb_bill = transition_labour_bill(token, feb_bill, 'approved')

    advance_rows = [('Samarjeet', 'Brickwork', 6000), ('Bihari', 'Labour Supplier', 15000), ('Rajender', 'Labour Supplier', 14000), ('Chhatrapal', 'Labour Supplier', 3000), ('Arvind Painter', 'Putty', 6000), ('Khokan', 'Waterproofing', 5000), ('Afsar', 'Shuttering', 19500), ('Khurshid', 'Steel', 18000), ('VK Enterprises', 'Brickwork', 9000), ('Giasiram', 'Tiles', 7000), ('Salman', 'Plumber', 2000), ('Monu', 'Door Shutter', 2000), ('Ganesh', 'Shuttering', 6000), ('Departmental', 'Helper', 14000), ('Umasankar', 'Glass', 3000), ('Anshu', 'Electrical', 5000), ('Aslam', 'Welder', 2000), ('Akram', 'Waterproofing', 4000), ('Mehanawaz', 'Tiles', 3000)]
    created_advances = []
    for idx, (name, nature, amount) in enumerate(advance_rows, start=1):
        created_advances.append(ensure_labour_advance(token, cache, advance_no=f'FOODADV-20260325-{idx:02d}', payload={'advance_no': f'FOODADV-20260325-{idx:02d}', 'project_id': project_id, 'contractor_id': contractors[name]['id'], 'advance_date': '2026-03-25', 'amount': amount, 'status': 'active', 'remarks': f'Weekly food advance - {nature}'}))

    anshu_payment_50k = ensure_payment(token, cache, contract_id=anshu_contract['id'], payment_date='2026-03-20', amount=50000, payment_mode='voucher', reference_no='Voucher 20-03-26', remarks='Voucher payment filed from source slip. Running context noted: Jan-26 13962, Feb-26 106862, post-credit balance 60824.')
    anshu_payment_50k = transition_payment(token, anshu_payment_50k, 'approved')
    anshu_payment_50k = transition_payment(token, anshu_payment_50k, 'released')
    summary_payments = [('Samarjeet', samarjeet_contract['id'], 11689, 'FEB,2026 FINAL'), ('Ganesh', ganesh_contract['id'], 79949, 'FEB,2026 FINAL'), ('Umasankar', uma_contract['id'], 25678, 'FEB,2026 FINAL'), ('Anshu', anshu_contract['id'], 13962, 'JAN,2026 FINAL')]
    summary_payment_rows = []
    for name, contract_id, amount, remarks in summary_payments:
        payment = ensure_payment(token, cache, contract_id=contract_id, payment_date='2026-03-25', amount=amount, payment_mode='summary', remarks=f'Payment summary entry - {remarks}')
        payment = transition_payment(token, payment, 'approved')
        payment = transition_payment(token, payment, 'released')
        summary_payment_rows.append(payment)

    files = {
        'drawing': r'c:\Users\yash\Downloads\WhatsApp Image 2026-04-02 at 12.44.36 PM.jpeg',
        'calc': r'c:\Users\yash\Downloads\WhatsApp Image 2026-03-29 at 11.09.05 AM.jpeg',
        'voucher': r'c:\Users\yash\Downloads\WhatsApp Image 2026-03-28 at 1.25.10 PM.jpeg',
        'feb_labour': r'c:\Users\yash\Downloads\WhatsApp Image 2026-03-28 at 1.18.14 PM (1).jpeg',
        'jan_labour': r'c:\Users\yash\Downloads\WhatsApp Image 2026-03-28 at 12.29.31 PM.jpeg',
        'email': r'c:\Users\yash\Downloads\WhatsApp Image 2026-03-27 at 7.00.44 PM (1).jpeg',
        'prw_summary': r'c:\Users\yash\Downloads\WhatsApp Image 2026-03-27 at 2.02.32 PM.jpeg',
        'food_summary': r'c:\Users\yash\Downloads\WhatsApp Image 2026-03-27 at 1.24.03 PM.jpeg',
        'uma_bill': r'c:\Users\yash\Downloads\WhatsApp Image 2026-03-27 at 11.38.00 AM.jpeg',
        'payment_summary': r'c:\Users\yash\Downloads\WhatsApp Image 2026-03-26 at 3.41.36 PM.jpeg',
        'roshni_quote': r'c:\Users\yash\Downloads\WhatsApp Image 2026-03-25 at 11.10.39 AM.jpeg',
    }
    ensure_document(token, cache, title='Structural Drawing Mark-up Reference', entity_type='company', entity_id=company_id, document_type='drawing', remarks='Site drawing reference from uploaded photo. Exact contract linkage not derived reliably from the image alone.', file_path=files['drawing'])
    ensure_document(token, cache, title='Handwritten Quantity Working - 1096 Cuft', entity_type='company', entity_id=company_id, document_type='measurement_working', remarks='Handwritten calc captured as reference: 23-7 x 6 x 7-9 = 1096 Cuft.', file_path=files['calc'])
    ensure_document(token, cache, title='Anshu Electrical Voucher - 20 Mar 2026', entity_type='payment', entity_id=anshu_payment_50k['id'], document_type='voucher', remarks='Source voucher image for released payment of 50000.', file_path=files['voucher'])
    ensure_document(token, cache, title='Departmental Labour Sheet - Feb 2026', entity_type='labour_bill', entity_id=feb_bill['id'], document_type='labour_sheet', remarks='Source image for February departmental labour bill.', file_path=files['feb_labour'])
    ensure_document(token, cache, title='Departmental Labour Sheet - Jan 2026', entity_type='labour_bill', entity_id=jan_bill['id'], document_type='labour_sheet', remarks='Source image for January departmental labour bill.', file_path=files['jan_labour'])
    ensure_document(token, cache, title='Email Reference - 8th RA Invoice and EPFO/ESIC', entity_type='company', entity_id=company_id, document_type='email_reference', remarks='Email screenshot referencing 8th RA verified copy and EPFO/ESIC challans.', file_path=files['email'])
    ensure_document(token, cache, title='PRW Paid Payment Summary - January 2026', entity_type='company', entity_id=company_id, document_type='payment_summary', remarks='Summary sheet spanning vendor and departmental labour payment posture.', file_path=files['prw_summary'])
    ensure_document(token, cache, title='Weekly Food Advance Summary - 25 Mar 2026', entity_type='company', entity_id=company_id, document_type='labour_advance_summary', remarks='Summary includes site expenses of 15000 that were kept only in the source document and not posted as structured labour advances.', file_path=files['food_summary'])
    ensure_document(token, cache, title='Uma Shankar 3rd RA Bill Sheet', entity_type='ra_bill', entity_id=ra_bill['id'], document_type='ra_bill_scan', remarks='Source image used for BOQ, measurement, and RA bill filing.', file_path=files['uma_bill'])
    ensure_document(token, cache, title='Payment Summary - 25 Mar 2026', entity_type='company', entity_id=company_id, document_type='payment_summary', remarks='Structured payments were filed where contract context was clear; departmental row remains handled on the labour side.', file_path=files['payment_summary'])
    ensure_document(token, cache, title='Roshni Enterprises Slip Quotation - 28 Mar 2026', entity_type='vendor', entity_id=roshni['id'], document_type='quotation', remarks='Slip quotation: 6 pcs panel, 6 pcs bazzi, total noted 2818.', file_path=files['roshni_quote'])

    print(json.dumps({
        'company_id': company_id,
        'project_id': project_id,
        'vendors': [roshni['name'], anshu_vendor['name'], uma_vendor['name'], samarjeet_vendor['name'], ganesh_vendor['name']],
        'contracts': [anshu_contract['contract_no'], uma_contract['contract_no'], samarjeet_contract['contract_no'], ganesh_contract['contract_no']],
        'measurement_no': measurement['measurement_no'],
        'ra_bill_no': ra_bill['bill_no'],
        'labour_attendance': [jan_attendance['muster_no'], feb_attendance['muster_no']],
        'labour_bills': [jan_bill['bill_no'], feb_bill['bill_no']],
        'labour_advances': len(created_advances),
        'payments': len(summary_payment_rows) + 1,
        'documents': len(cache['documents']),
    }, indent=2))

if __name__ == '__main__':
    main()

