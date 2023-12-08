from flask import Flask, jsonify, request
from database import db
from flask_mail import Mail, Message
import pyotp
import hashlib
import jwt
from datetime import datetime,timedelta
from functools import wraps

app = Flask(__name__)
# Generate Secret Key
app.config['SECRET_KEY'] = '<insert 32byte string from random generator'

# Email Configuration 
app.config['MAIL_SERVER'] ='stmp,gmail.com'
app.config['MAIL_PORT'] = 'insert port value'
app.config['MAIL_USERNAME'] = '<insert value>'
app.config['MAIL_PASSWORD'] = '<insert value>'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

mail = Mail(app)
skey= pyotp.random_base32()
totp = pyotp.TOTP(skey,interval=750)



# Mendapatkan record berdasarkan parameter yang diinginkan
@app.route("/users", methods=['GET'])
def users():
    cur = db.cursor()
    id_user = request.args.get("id_user")
    cur.execute(f'''
                SELECT * FROM pelanggar WHERE email = '{id_user}'; 
                ''')
    columns = cur.descriptions()
    data = cur.fetchall()
    result = []
    for value in data:
        tmp ={}
        for (index,column) in enumerate(value):
            tmp[columns[index][0]] = column
            result.append(tmp)
    return jsonify(result)

# Mendaftarkan pelanggaran baru
@app.route("/add-violations", methods=['POST'])
def add_violation():
    try: 
        cur = db.cursor()
        data = request.json
        id_violation = data["id_violation"]
        date = data["date"]
        time = data["time"]
        picture = data["picture"]
        type = data["type"]
        status = data["status"]
        cur.execute(f'''
                INSERT INTO pelanggaran
                (id_violation,date,time,picture, type, status)
                VALUES ({id_violation},{date},{time},'{picture}',{type},{status});
                ''')
    except Exception as e:
        print(e)
        return({"message": str(e)})
    return jsonify({"message": f"Success adding new violation record with id: {id_violation}"})


# Mengupdate handling status violation record
@app.route("/status", methods=['PUT'])
def edit_violation():
    try: 
        cur = db.cursor()
        data = request.json
        id_violation = data["id_violation"]
        date = data["date"]
        time = data["time"]
        picture = data["picture"]
        type = data["type"]
        status = data["status"]
        cur.execute(f'''
                    SELECT * from pelanggaran
                    WHERE id_violation = '{id_violation}'
                    AND date = {date}
                    AND time= {time}
                    AND picture = {picture}
                    AND type = '{type}';
                    ''')
        check_data = cur.fetchall()
        if len(check_data) == 1:
            cur.execute(f'''
                        UPDATE pelanggaran
                        SET status = '{status}'
                        WHERE id_violation = '{id_violation}' 
                        ''')
        else: 
            raise Exception(
				f'Record violation on {date}, {time} and violation id: {id_violation} is NOT EXIST'
			)
    except Exception as e:
        print(e)
        return({"message": str(e)})
    return jsonify({"message": f"Succesfully updated record violation on {date},{time}and violation id : {id_violation}"})

# Mengirimkan notifikasi
@app.route("/send-email", methods=['POST'])
def send_email():
    try: 
        cur = db.cursor()
        data = request.json
        email = data["email"]
        violation_code = data["violation_charged_Code"]
        year = data["violation_year"]
        month = data["violation_month"]
        day_of_week = data["violation_day_of_week"]
        location = data["state_of_license"]
        report = data["police_agency"]
        cur.execute(f'''
                    SELECT handling_status FROM pelanggar_traffic_empat_tahun 
                    WHERE email = '{email}'
                    AND violation_charged_Code = {violation_code}
                    AND violation_year= {year}
                    AND violation_month = {month}
                    AND violation_day_of_week = '{day_of_week}'
                    AND state_of_license = '{location}'
                    AND police_agency = '{report}';;
                    ''')
        check_data = cur.fetchall()
        if len(check_data) == "NOTPAID":
            data = cur.fetchall()
            msg = Message(
            'Smart Ticketing System',
			sender = app.config['MAIL_USERNAME'],
			recipients = {email})
            msg.body = f'''
            Halo '{email}'!
            Telah tertulis bahwa Anda melakukan pelanggaran lalu lintas dengan keterangan :
            Tanggal : '{day_of_week}'/{month}/{year}
            Tipe Pelanggaran : {violation_code}
            Silahkan melakukan penanganan terhadap pelanggaran Anda ke kantor polici '{report}'.
            Terima kasih.'''
            mail.send(msg)
            return jsonify({"message" : "Email have been sent to trafic violator."})
        else :
            raise Exception(
				f'Violation case has been handled.'
			)
    except Exception as e:
        print(e)
        return({"message": str(e)})

# User Authentication using Sign Up API

def hash_password(password):
    sha256 = hashlib.sha256()
    sha256.update(password.encode())
    hashed_password = sha256.hexdigest()
    return hashed_password

@app.route("/sign-up", methods=['POST'])
def signup():
    try: 
        cur = db.cursor()
        data = request.json
        email = data["email"]
        username = data["username"]
        password = data["password"]
        cur.execute(f'''
                    SELECT * from data_user 
                    WHERE email = '{email}'
                    OR username = '{username}';
                ''')
        check_data = cur.fetchall()
        if len(check_data) == 1:
            cur.execute(f'''
                        INSERT INTO data_user(email,username,password)
                		VALUES ('{email}','{username}','{hash_password(password)}');
                        ''')
            db.commit()
        else: 
            raise Exception(
				f'User already registered. Please sign-in.'
			)
    except Exception as e:
        print(e)
        return({"message": str(e)})
    return jsonify({"message": f"Successfully register user!"})

# User Authentication Sign In API
# Generate Secret Key
app.config['SECRET_KEY'] = '<insert 32byte string from random generator'

@app.route("/sign-in", methods=['POST'])
def signin():
    try: 
        cur = db.cursor()
        data = request.json
        username = data["username"]
        password = data["password"]
        cur.execute(f'''
                    SELECT * from data_user 
                    WHERE username = '{username}';
                ''')
        columns = cur.description
        data = cur.fetchall()
        user = None
        for value in data:
            tmp ={}
            for (index,column) in enumerate(value):
                tmp[columns[index][0]] = column
            user = tmp
            break
        if user:
            if user['password'] == hash_password(password):
                token = jwt.encode({
					'user_id' : user['id'],
					'exp' : datetime.utcnow() + timedelta(minutes = 75)}, app.config['SECRET_KEY'])
                return jsonify({"token": token})
            else: 
                raise Exception(
					f'Wrong username or password. Please input right username or password.'
				)
        else: 
            raise Exception(
				f'Wrong username or password. Please input right username or password.'
			)
    except Exception as e:
        print(e)
        return({"message": str(e)})

# Generate token
def required_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
        if not token:
            return jsonify({'error' : 'Token required!'}), 401
        
        try :
            token = token.replace('Bearer ', '')
            data = jwt.decode(token, app.config['SECRET KEY'], algorithmns = ['HS256'])
            cur = db.cursor
            cur.execute(f'''SELECT * FROM data_user 
                        	WHERE id = {data['user_id']};
                         ''')
            columns = cur.description
            data = cur.fetchall()
            user = None
            for value in data:
                tmp ={}
                for (index,column) in enumerate(value):
                    tmp[columns[index][0]] = column
                user = tmp
                break
        except:
            return jsonify({'error': 'Invalid token!'}), 401
        return f(user,*args, **kwargs)
    return decorated


# Authentication Sign In with Authorization OTP
@app.route("/sign-in-otp", methods=['POST'])
def signin_otp():
    try: 
        cur = db.cursor()
        data = request.json
        username = data["username"]
        password = data["password"]
        cur.execute(f'''
                    SELECT * from data_user 
                    WHERE username = '{username}';
                ''')
        columns = cur.description
        data = cur.fetchall()
        user = None
        for value in data:
            tmp ={}
            for (index,column) in enumerate(value):
                tmp[columns[index][0]] = column
            user = tmp
            break
        if user:
            if user['password'] == hash_password(password):
                msg = Message( 'Smart Ticketing System',
				sender = app.config['MAIL_USERNAME'],
				recipients = [user['email']])
                user_otp = totp.now()
                msg.body = f'Your OTP code is: {user_otp}. Please to not share this to anyone. Your OTP will only available for 75 seconds'
                mail.send(msg)
                return jsonify({"message": "Silahkan memasukkan OTP yang telah dikirim"})
            else : 
                raise Exception(
					f'Wrong username or password! Please try again.'
				)
        else: 
            raise Exception(
				f'Wrong username or password! Please try again.'
			)
    except Exception as e:
        print(e)
        return({"message": str(e)})
    
# Verify OTP
@app.route("/verify-otp", methods=['GET'])
def verify_otp(): 
    cur = db.cursor()
    data = request.json
    username = data["username"]
    otp = data["otp"]
    cur.execute(f'''
                SELECT * from data_user 
                WHERE username = '{username}';
                ''')
    columns = cur.description
    data = cur.fetchall()
    user = None
    for value in data :
        tmp = {}
        for (index, column) in enumerate(value):
            tmp[columns[index][0]] = column
        user = tmp
        break
    if not user:
        return (jsonify({'error' : 'Account is not existed'}), 401)
    if totp.verify(otp):
        token = jwt.encode({
            'user_id' : user['id'],
			'exp' : datetime.utcnow() + timedelta(minutes = 75)
    		}, app.config['SECRET_KEY'])
        return jsonify({'access_token': token})
    return (jsonify({'error' : 'Wrong OTP.'}), 401)

if __name__ == '__main__':
    app.run(debug=True, load_dotenv=True)