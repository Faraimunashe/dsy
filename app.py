from flask import Flask, jsonify, request, redirect, render_template, url_for, flash, session,wrappers
from flask_session import Session
from flask_login import LoginManager, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from models import *
from functools import wraps
import pandas as pd
import os
import random
import numpy as np
from converter import *
from PIL import Image, ImageDraw, ImageFont
from pydub import AudioSegment
import os
import tempfile

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ProfessorSecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:''@localhost/dys_db'


db.init_app(app)


login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(id=user_id).first()

#check roles
def admin_role(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        user = User.query.filter_by(id=session['userid']).first()
        if user.role == 1:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('student_dashboard'))
    return decorated_func


def generate_words_from_model():
    words = Word.query.with_entities(Word.characters).order_by(db.func.random()).limit(10).all()
    formatted_words = [word[0] for word in words]
    return formatted_words


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email == '' or password == '':
            flash('some fields are empty.')
            return redirect(url_for('login'))

        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('Invalid login details.')
            return redirect(url_for('login'))
        if check_password_hash(user.password, password):
            login_user(user)
            session['userid'] = user.id
            return redirect(url_for('admin_dashboard'))

        flash('Invalid login details.')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
		
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password_confirmation')
		

        if password != password2:
            flash('Password confirmation should match!')
            return redirect(url_for('register'))

        if len(password) <= 7:
            flash('Password should be 8 characters or greater!')
            return redirect(url_for('register'))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists!')
            return redirect(url_for('register'))
        new_user = User(email=email, password=generate_password_hash(password, method='sha256'), name=name, role=request.form.get('role'))
        db.session.add(new_user)
        db.session.commit()

        flash('Successfully registered new user!')
        return redirect(url_for('login'))
    return render_template('register.html')



@app.route("/")
def home():
	file1 = "./lists/dictation_answers.csv"
	file2 = "./lists/words.csv"
	answer_list = ["-", "-", "-", "-", "-", "-", "-", "-", "-", "-"]
	dct = {"Answers": answer_list}
	df = pd.DataFrame(dct)
	df.to_csv(file1, mode='w', index=False)

	wow = "./lists/web_of_words.csv"
	df_w = pd.read_csv(wow)
	list_wow = []
	list_word = []
	length_w = df_w.shape[0]
	for i in range(length_w):
		list_wow.append(df_w.iat[i, 0])

	for i in range(10):
		rand_word = random.choice(list_wow)
		list_word.append(rand_word)
		list_wow.remove(rand_word)

	dict_word = {'Words': list_word}
	df_word = pd.DataFrame(dict_word)
	df_word.to_csv(file2, mode='w', index=False)
	return render_template("index.html")


@app.route("/teacher-dashboard", methods=["GET", "POST"])
@login_required
@admin_role
def admin_dashboard():

	results = db.session.query(User.name, db.func.count(Mark.id), Session.id).\
		join(Session, User.id == Session.userid).\
		join(Mark, Session.id == Mark.sessionid).\
		filter(Mark.passed == True).\
		group_by(Session.id).\
	all()
	return render_template("teacher_dash.html", results=results)


@app.route("/results/<sessionid>", methods=["GET"])
@login_required
@admin_role
def admin_results(sessionid):

	marks = Mark.query.filter_by(sessionid = sessionid).all()
	words = Word.query.all()
	return render_template("admin_results.html", marks=marks, sessionid=sessionid, words=words)


@app.route("/student-dashboard", methods=["GET", "POST"])
def student_dashboard():

	return render_template("student_dash.html")







@app.route("/listen", methods=["GET", "POST"])
@login_required
def listen():

	if request.method == "POST":

		i =1

		new_session = Session(userid=session['userid'])
		db.session.add(new_session)
		db.session.commit()

		while i < 11:
			word_id = request.form.get('a'+str(i))
			ans = request.form.get(str(i))
			passed = False
			
			w = Word.query.filter_by(id=word_id).first()
			if ans == w.characters:
				passed = True

			new_mark = Mark(sessionid=new_session.id, wordid=word_id, passed=passed, answer=ans)
			db.session.add(new_mark)
			db.session.commit()
			i+= 1
	
		marks = Mark.query.filter_by(sessionid=new_session.id).all()
		words = Word.query.all()
		return render_template("result1.html", marks=marks, words=words)

	
	
	words = Word.query.order_by(db.func.random()).limit(10).all()
	return render_template("listen.html", words=words)


@app.route("/therapy", methods=["GET", "POST"])
@login_required
def therapy():

	if request.method == "POST":
		# audio_file = request.files['audio']

		# # audio_data = AudioSegment.from_wav(audio_file)
		# # audio_path = os.path.join('public', 'recording.mp3')
		# # audio_data.export(audio_path, format='mp3')

		# name = random.randint(1000,9999)
		# audio_file.save('static/'+str(name)+'.mp3')

		audio = request.files['audio']

		# Save uploaded audio to a temporary file
		temp_file = tempfile.NamedTemporaryFile(delete=False)
		audio.save(temp_file.name)

		# Convert WAV to MP3
		audio_data = AudioSegment.from_wav(temp_file.name)
		audio_path = os.path.join('static/therapy', 'recording.mp3')
		audio_data.export(audio_path, format='mp3')

		# Remove the temporary file
		os.remove(temp_file.name)

		return render_template("therapy_rs.html")

	
	
	return render_template("therapy.html")




@app.route("/result1")
def result1(a_1=None, b_1=None, c_1=None, a_2=None, b_2=None, c_2=None, a_3=None, b_3=None, c_3=None, a_4=None, b_4=None, c_4=None, a_5=None, b_5=None, c_5=None, a_6=None, b_6=None, c_6=None, a_7=None, b_7=None, c_7=None, a_8=None, b_8=None, c_8=None, a_9=None, b_9=None, c_9=None, a_10=None, b_10=None, c_10=None):
	file1 = './lists/dictation_answers.csv'
	file2 = './lists/words.csv'
	df1 = pd.read_csv(file1)
	df1 = df1.replace(np.nan, '', regex=True)
	df2 = pd.read_csv(file2)


	a1 = df1.iat[0, 0]
	b1 = df2.iat[0, 0]
	if a1.lower() == b1.lower():
		c1 = 'Perfection'
	else:
		c1 = 'We will improve!'

	a2 = df1.iat[1, 0]
	b2 = df2.iat[1, 0]
	if a2.lower() == b2.lower():
		c2 = 'Perfection'
	else:
		c2 = 'We will improve!'

	a3 = df1.iat[2, 0]
	b3 = df2.iat[2, 0]
	if a3.lower() == b3.lower():
		c3 = 'Perfection'
	else:
		c3 = 'We will improve!'

	a4 = df1.iat[3, 0]
	b4 = df2.iat[3, 0]
	if a4.lower() == b4.lower():
		c4 = 'Perfection'
	else:
		c4 = 'We will improve!'

	a5 = df1.iat[4, 0]
	b5 = df2.iat[4, 0]
	if a5.lower() == b5.lower():
		c5 = 'Perfection'
	else:
		c5 = 'We will improve!'

	a6 = df1.iat[5, 0]
	b6 = df2.iat[5, 0]
	if a6.lower() == b6.lower():
		c6 = 'Perfection'
	else:
		c6 = 'We will improve!'

	a7 = df1.iat[6, 0]
	b7 = df2.iat[6, 0]
	if a7.lower() == b7.lower():
		c7 = 'Perfection'
	else:
		c7 = 'We will improve!'

	a8 = df1.iat[7, 0]
	b8 = df2.iat[7, 0]
	if a8.lower() == b8.lower():
		c8 = 'Perfection'
	else:
		c8 = 'We will improve!'

	a9 = df1.iat[8, 0]
	b9 = df2.iat[8, 0]
	if a9.lower() == b9.lower():
		c9 = 'Perfection'
	else:
		c9 = 'We will improve!'

	a10 = df1.iat[9, 0]
	b10 = df2.iat[9, 0]
	if a10.lower() == b10.lower():
		c10 = 'Perfection'
	else:
		c10 = 'We will improve!'

	file_check = './lists/table.csv'
	df_check = pd.read_csv(file_check)
	length_check = df_check.shape[0]
	for i in range(length_check):
		df_check.iat[i, 5] = 0
	df_check.to_csv(file_check, mode='w', index=False)

	df = pd.read_csv(file1)
	df = df.replace(np.nan, '', regex=True)
	length=df.shape[0]
	for i in range(length):
		df.iat[i, 0] = '-'
	df.to_csv(file1, mode='w', index=False)

	wow = "./lists/web_of_words.csv"
	df_w = pd.read_csv(wow)
	list_wow = []
	list_word = []
	length_w = df_w.shape[0]
	for i in range(length_w):
		list_wow.append(df_w.iat[i, 0])

	for i in range(10):
		rand_word = random.choice(list_wow)
		list_word.append(rand_word)
		list_wow.remove(rand_word)

	dict_word = {'Words': list_word}
	df_word = pd.DataFrame(dict_word)
	df_word.to_csv(file2, mode='w', index=False)

	return render_template("result1.html", a_1=a1, b_1=b1, c_1=c1, a_2=a2, b_2=b2, c_2=c2, a_3=a3, b_3=b3, c_3=c3, a_4=a4, b_4=b4, c_4=c4, a_5=a5, b_5=b5, c_5=c5, a_6=a6, b_6=b6, c_6=c6, a_7=a7, b_7=b7, c_7=c7, a_8=a8, b_8=b8, c_8=c8, a_9=a9, b_9=b9, c_9=c9, a_10=a10, b_10=b10, c_10=c10)





@app.route("/read", methods=["GET", "POST"])
@login_required
def read(image=None):

	if request.method == "POST":
		i =1

		new_session = Session(userid=session['userid'])
		db.session.add(new_session)
		db.session.commit()

		while i < 11:
			wordr = request.form.get('a'+str(i))
			ans = request.form.get(str(i))
			passed = False
			
			w = Word.query.filter_by(characters=wordr).first()
			if ans == w.characters:
				passed = True

			new_mark = Mark(sessionid=new_session.id, wordid=w.id, passed=passed, answer=ans)
			db.session.add(new_mark)
			db.session.commit()
			i+= 1
	
		marks = Mark.query.filter_by(sessionid=new_session.id).all()
		words = Word.query.all()
		return render_template("result4.html", marks=marks, words=words)
	else:
		# Generate words from your model
		words = generate_words_from_model()

		# Set up image dimensions and font
		width, height = 800, 600
		background_color = (255, 255, 255)  # White background color
		text_color = (0, 0, 0)  # Black text color
		font_size = 30
		font_path = "static/pacifico.ttf"  # Replace with your font file path
		font = ImageFont.truetype(font_path, font_size)

		# Create a new image
		image = Image.new('RGB', (width, height), background_color)
		draw = ImageDraw.Draw(image)

		# Calculate starting position for vertical centering
		text_height = sum(font.getsize(w)[1] for w in words)
		y = (height - text_height) // 2

		# Write each word on the image
		for word in words:
			text_width, text_height = draw.textsize(word, font=font)
			x = (width - text_width) // 2
			draw.text((x, y), word, font=font, fill=text_color)
			y += text_height  # Move down for the next word

		# Save the image
		image_path = "./static/img/generated_image.jpeg"  # Path to save the generated image
		image.save(image_path)

		# Render the image template with the saved image path
		return render_template('read.html', image=image_path, words=words)

@app.route("/student", methods=["GET", "POST"])
@login_required
def student():
	
	return redirect(url_for("student_dashboard"))

@app.route("/instructions_1", methods=["GET", "POST"])
def instructions_1():

	file_check = './lists/table.csv'
	df_check = pd.read_csv(file_check)
	length_check = df_check.shape[0]
	for i in range(length_check):
		df_check.iat[i, 5] = 0
	df_check.to_csv(file_check, mode='w', index=False)
	file1 = "./lists/dictation_answers.csv"
	df = pd.read_csv(file1)
	length=df.shape[0]
	for i in range(length):
		df.iat[i, 0] = '-'
	df.to_csv(file1, mode='w', index=False)

	wow = "./lists/web_of_words.csv"
	file2 = "./lists/words.csv"
	df_w = pd.read_csv(wow)
	list_wow = []
	list_word = []
	length_w = df_w.shape[0]
	for i in range(length_w):
		list_wow.append(df_w.iat[i, 0])

	for i in range(10):
		rand_word = random.choice(list_wow)
		list_word.append(rand_word)
		list_wow.remove(rand_word)

	dict_word = {'Words': list_word}
	df_word = pd.DataFrame(dict_word)
	df_word.to_csv(file2, mode='w', index=False)
	return render_template("instructions_1.html")

@app.route("/instructions_2", methods=["GET", "POST"])
def instructions_2():

	file_check = './lists/table.csv'
	df_check = pd.read_csv(file_check)
	length_check = df_check.shape[0]
	for i in range(length_check):
		df_check.iat[i, 5] = 0
	df_check.to_csv(file_check, mode='w', index=False)
	file1 = "./lists/dictation_answers.csv"
	df = pd.read_csv(file1)
	length=df.shape[0]
	for i in range(length):
		df.iat[i, 0] = '-'
	df.to_csv(file1, mode='w', index=False)

	wow = "./lists/web_of_words.csv"
	file2 = "./lists/words.csv"
	df_w = pd.read_csv(wow)
	list_wow = []
	list_word = []
	length_w = df_w.shape[0]
	for i in range(length_w):
		list_wow.append(df_w.iat[i, 0])

	for i in range(10):
		rand_word = random.choice(list_wow)
		list_word.append(rand_word)
		list_wow.remove(rand_word)

	dict_word = {'Words': list_word}
	df_word = pd.DataFrame(dict_word)
	df_word.to_csv(file2, mode='w', index=False)
	return render_template("instructions_2.html")

@app.route("/teacher", methods=["GET", "POST"])
def teacher():

	file_check = './lists/table.csv'
	df_check = pd.read_csv(file_check)
	length_check = df_check.shape[0]
	for i in range(length_check):
		df_check.iat[i, 5] = 0
	df_check.to_csv(file_check, mode='w', index=False)
	file1 = "./lists/dictation_answers.csv"
	df = pd.read_csv(file1)
	length=df.shape[0]
	for i in range(length):
		df.iat[i, 0] = '-'
	df.to_csv(file1, mode='w', index=False)

	wow = "./lists/web_of_words.csv"
	file2 = "./lists/words.csv"
	df_w = pd.read_csv(wow)
	list_wow = []
	list_word = []
	length_w = df_w.shape[0]
	for i in range(length_w):
		list_wow.append(df_w.iat[i, 0])

	for i in range(10):
		rand_word = random.choice(list_wow)
		list_word.append(rand_word)
		list_wow.remove(rand_word)

	dict_word = {'Words': list_word}
	df_word = pd.DataFrame(dict_word)
	df_word.to_csv(file2, mode='w', index=False)
	return render_template("teacher.html")

@app.route("/teacher_1", methods=["GET", "POST"])
@login_required
@admin_role
def teacher_1():

	file_check = './lists/table.csv'
	df_check = pd.read_csv(file_check)
	length_check = df_check.shape[0]
	for i in range(length_check):
		df_check.iat[i, 5] = 0
	df_check.to_csv(file_check, mode='w', index=False)

	file1 = "./lists/dictation_answers.csv"
	df = pd.read_csv(file1)
	length=df.shape[0]
	for i in range(length):
		df.iat[i, 0] = '-'
	df.to_csv(file1, mode='w', index=False)

	wow = "./lists/web_of_words.csv"
	file2 = "./lists/words.csv"
	df_w = pd.read_csv(wow)
	list_wow = []
	list_word = []
	length_w = df_w.shape[0]
	for i in range(length_w):
		list_wow.append(df_w.iat[i, 0])

	for i in range(10):
		rand_word = random.choice(list_wow)
		list_word.append(rand_word)
		list_wow.remove(rand_word)

	dict_word = {'Words': list_word}
	df_word = pd.DataFrame(dict_word)
	df_word.to_csv(file2, mode='w', index=False)
	return render_template("teacher_1.html")

@app.route("/teacher_2", methods=["GET", "POST"])
def teacher_2():

	file_check = './lists/table.csv'
	df_check = pd.read_csv(file_check)
	length_check = df_check.shape[0]
	for i in range(length_check):
		df_check.iat[i, 5] = 0
	df_check.to_csv(file_check, mode='w', index=False)


	file1 = "./lists/dictation_answers.csv"
	df = pd.read_csv(file1)
	length=df.shape[0]
	for i in range(length):
		df.iat[i, 0] = '-'
	df.to_csv(file1, mode='w', index=False)

	wow = "./lists/web_of_words.csv"
	file2 = "./lists/words.csv"
	df_w = pd.read_csv(wow)
	list_wow = []
	list_word = []
	length_w = df_w.shape[0]
	for i in range(length_w):
		list_wow.append(df_w.iat[i, 0])

	for i in range(10):
		rand_word = random.choice(list_wow)
		list_word.append(rand_word)
		list_wow.remove(rand_word)

	dict_word = {'Words': list_word}
	df_word = pd.DataFrame(dict_word)
	df_word.to_csv(file2, mode='w', index=False)
	return render_template("teacher_2.html")

@app.route("/teacher_3", methods=["GET", "POST"])
def teacher_3(x=None):

	file_check = './lists/table.csv'
	df_check = pd.read_csv(file_check)
	length_check = df_check.shape[0]
	for i in range(length_check):
		df_check.iat[i, 5] = 0
	df_check.to_csv(file_check, mode='w', index=False)

	file1 = "./lists/dictation_answers.csv"
	df = pd.read_csv(file1)
	length=df.shape[0]
	for i in range(length):
		df.iat[i, 0] = '-'
	df.to_csv(file1, mode='w', index=False)

	wow = "./lists/web_of_words.csv"
	file2 = "./lists/words.csv"
	df_w = pd.read_csv(wow)
	list_wow = []
	list_word = []
	length_w = df_w.shape[0]
	for i in range(length_w):
		list_wow.append(df_w.iat[i, 0])

	for i in range(10):
		rand_word = random.choice(list_wow)
		list_word.append(rand_word)
		list_wow.remove(rand_word)

	dict_word = {'Words': list_word}
	df_word = pd.DataFrame(dict_word)
	df_word.to_csv(file2, mode='w', index=False)

	file_check = './lists/table.csv'
	df_check = pd.read_csv(file_check)
	length = df_check.shape[0]
	print(length)
	nam = df_check.iat[length-1, 0]
	print(nam)
	return render_template("teacher_3.html", x=nam)

@app.route("/addwords", methods=["GET", "POST"])
@login_required
@admin_role
def addwords():
	if request.method == 'POST':
		inp = request.form.get('inputWords')
		if(inp is None):
			flash('error input cannot be null')
			return redirect(url_for(addwords))
		
		word = Word.query.filter_by(characters=inp).first()
		if word != None:
			flash('error word already exist!')
			return redirect(url_for('addwords'))
		
		path = 'static/'
		num = random.randint(1000000000, 9999999999)
		extension = '.mp3'

		audio = path+str(num)+extension
		try:
			convert_text_to_speech(text=inp, filename=audio)
		except:
			flash('error text to speech error!')
			return redirect(url_for('addwords'))
		
		new_word = Word(characters=inp, file=audio)
    	
		db.session.add(new_word)
		db.session.commit()
		return redirect(url_for("addwords"))
	else:
		return render_template("addwords.html")

@app.route("/list-words", methods=["GET"])
@login_required
@admin_role
def list_words():
	
	words = Word.query.all()
	return render_template("list_word.html", words=words)


@app.route("/addwords_2", methods=["GET", "POST"])
def addwords_2():

	if request.method == 'POST':
		rio = []
		dict_check = {'Name': [], 'Number': [], 'Image': [], 'Text File': [], 'CSV File': []}
		for i in range(10):
			rio.append('')
		rio[0] = request.form.getlist("riWord_1")[0]
		rio[1] = request.form.getlist("riWord_2")[0]
		rio[2] = request.form.getlist("riWord_3")[0]
		rio[3] = request.form.getlist("riWord_4")[0]
		rio[4] = request.form.getlist("riWord_5")[0]
		rio[5] = request.form.getlist("riWord_6")[0]
		rio[6] = request.form.getlist("riWord_7")[0]
		rio[7] = request.form.getlist("riWord_8")[0]
		rio[8] = request.form.getlist("riWord_9")[0]
		rio[9] = request.form.getlist("riWord_10")[0]

		file_check = './lists/table.csv'
		isExist1 = os.path.exists(file_check)
		if isExist1 == False:
			nam = 'read1'
			num = 1
			dir_n = './lists/read1'
			os.mkdir(dir_n)
			img = './static/img/read1.jpeg'
			textf = './lists/read1/read1.txt'
			os.mknod(textf)
			csvf = './lists/read1/read1.csv'
			u = 0
			with open(textf, 'w') as the_file:
				for i in range(10):
					line = rio[i]+'\n'
					the_file.write(line)

			dict_csvf = {'Words': rio}
			df_csvf = pd.DataFrame(dict_csvf)
			df_csvf.to_csv(csvf, mode='w', index=False)
			dict_check = {'Name': [nam], 'Number': [num], 'Image': [img], 'Text File': [textf], 'CSV File': [csvf], 'Use': [u]}
			df_check = pd.DataFrame(dict_check)
			df_check.to_csv(file_check, mode='w', index=False)

		else:
			df_c = pd.read_csv(file_check)
			length_c = df_c.shape[0]
			l_num = df_c.iat[length_c - 1, 1]
			s = 'length = ' + str(l_num)
			print(s)
			num = l_num + 1
			read_n = 'read' + str(num)
			dir_name = './lists/' + read_n
			os.mkdir(dir_name)
			textf = dir_name + '/' + read_n + '.txt'
			os.mknod(textf)
			csvf = dir_name + '/' + read_n + '.csv'
			img =  './static/img/' + read_n + '.jpeg'
			u = 0
			with open(textf, 'w') as the_file:
				for i in range(10):
					line = rio[i]+'\n'
					the_file.write(line)

			dict_csvf = {'Words': rio}
			df_csvf = pd.DataFrame(dict_csvf)
			df_csvf.to_csv(csvf, mode='w', index=False)
			dict_c1 = {'Name': [read_n], 'Number': [num], 'Image': [img], 'Text File': [textf], 'CSV File': [csvf], 'Use': [u] }
			df_c1 = pd.DataFrame(dict_c1)
			df_c1.to_csv(file_check, mode='a', header=False, index=False)
		return redirect(url_for('teacher_3'))


	else:
		file1 = "./lists/dictation_answers.csv"
		df = pd.read_csv(file1)
		length=df.shape[0]
		for i in range(length):
			df.iat[i, 0] = '-'
		df.to_csv(file1, mode='w', index=False)

		wow = "./lists/web_of_words.csv"
		file2 = "./lists/words.csv"
		df_w = pd.read_csv(wow)
		list_wow = []
		list_word = []
		length_w = df_w.shape[0]
		for i in range(length_w):
			list_wow.append(df_w.iat[i, 0])

		for i in range(10):
			rand_word = random.choice(list_wow)
			list_word.append(rand_word)
			list_wow.remove(rand_word)

		dict_word = {'Words': list_word}
		df_word = pd.DataFrame(dict_word)
		df_word.to_csv(file2, mode='w', index=False)
		return render_template("addwords_2.html")

@app.route("/about", methods=["GET", "POST"])
def about():

	file_check = './lists/table.csv'
	df_check = pd.read_csv(file_check)
	length_check = df_check.shape[0]
	for i in range(length_check):
		df_check.iat[i, 5] = 0
	df_check.to_csv(file_check, mode='w', index=False)

	file1 = "./lists/dictation_answers.csv"
	df = pd.read_csv(file1)
	length=df.shape[0]
	for i in range(length):
		df.iat[i, 0] = '-'
	df.to_csv(file1, mode='w', index=False)

	wow = "./lists/web_of_words.csv"
	file2 = "./lists/words.csv"
	df_w = pd.read_csv(wow)
	list_wow = []
	list_word = []
	length_w = df_w.shape[0]
	for i in range(length_w):
		list_wow.append(df_w.iat[i, 0])

	for i in range(10):
		rand_word = random.choice(list_wow)
		list_word.append(rand_word)
		list_wow.remove(rand_word)

	dict_word = {'Words': list_word}
	df_word = pd.DataFrame(dict_word)
	df_word.to_csv(file2, mode='w', index=False)
	return render_template("about.html")

@app.route("/result2", methods=["GET", "POST"])
def result2():

	file_check = './lists/table.csv'
	df_check = pd.read_csv(file_check)
	length_check = df_check.shape[0]
	for i in range(length_check):
		df_check.iat[i, 5] = 0
	df_check.to_csv(file_check, mode='w', index=False)

	file1 = "./lists/dictation_answers.csv"
	df = pd.read_csv(file1)
	length=df.shape[0]
	for i in range(length):
		df.iat[i, 0] = '-'
	df.to_csv(file1, mode='w', index=False)

	wow = "./lists/web_of_words.csv"
	file2 = "./lists/words.csv"
	df_w = pd.read_csv(wow)
	list_wow = []
	list_word = []
	length_w = df_w.shape[0]
	for i in range(length_w):
		list_wow.append(df_w.iat[i, 0])

	for i in range(10):
		rand_word = random.choice(list_wow)
		list_word.append(rand_word)
		list_wow.remove(rand_word)

	dict_word = {'Words': list_word}
	df_word = pd.DataFrame(dict_word)
	df_word.to_csv(file2, mode='w', index=False)
	return render_template("result2.html")


@app.route("/result4")
def result4(x_1=None, y_1=None, z_1=None, x_2=None, y_2=None, z_2=None, x_3=None, y_3=None, z_3=None, x_4=None, y_4=None, z_4=None, x_5=None, y_5=None, z_5=None, x_6=None, y_6=None, z_6=None, x_7=None, y_7=None, z_7=None, x_8=None, y_8=None, z_8=None, x_9=None, y_9=None, z_9=None, x_10=None, y_10=None, z_10=None):
	 
	file_check = './lists/table.csv'
	df_check = pd.read_csv(file_check)
	length_check = df_check.shape[0]
	val = 0
	for i in range(length_check):
		val = i
		if df_check.iat[i, 5] == 1:
			break

	for i in range(length_check):
		df_check.iat[i, 5] = 0
	df_check.to_csv(file_check, mode='w', index=False)
	u = val + 1
	name = 'read' + str(u) 
	print(name)
	file11 = './lists/'+ name + '/answers.csv'
	file12 = './lists/'+ name + '/' + name + '.csv'
	print(file12)
	df11 = pd.read_csv(file11)
	df11 = df11.replace(np.nan, '', regex=True)
	df12 = pd.read_csv(file12)
	print(df11)
	print(df12)

	x1 = df11.iat[0, 0]
	y1 = df12.iat[0, 0]
	if x1 == y1:
		z1 = 'Perfection'
	else:
		z1 = 'We will improve!'

	x2 = df11.iat[1, 0]
	y2 = df12.iat[1, 0]
	if x2 == y2:
		z2 = 'Perfection'
	else:
		z2 = 'We will improve!'

	x3 = df11.iat[2, 0]
	y3 = df12.iat[2, 0]
	if x3 == y3:
		z3 = 'Perfection'
	else:
		z3 = 'We will improve!'

	x4 = df11.iat[3, 0]
	y4 = df12.iat[3, 0]
	if x4 == y4:
		z4 = 'Perfection'
	else:
		z4 = 'We will improve!'

	x5 = df11.iat[4, 0]
	y5 = df12.iat[4, 0]
	if x5 == y5:
		z5 = 'Perfection'
	else:
		z5 = 'We will improve!'

	x6 = df11.iat[5, 0]
	y6 = df12.iat[5, 0]
	if x6 == y6:
		z6 = 'Perfection'
	else:
		z6 = 'We will improve!'

	x7 = df11.iat[6, 0]
	y7 = df12.iat[6, 0]
	if x7 == y7:
		z7 = 'Perfection'
	else:
		z7 = 'We will improve!'

	x8 = df11.iat[7, 0]
	y8 = df12.iat[7, 0]
	if x8 == y8:
		z8 = 'Perfection'
	else:
		z8 = 'We will improve!'

	x9 = df11.iat[8, 0]
	y9 = df12.iat[8, 0]
	if x9 == y9:
		z9 = 'Perfection'
	else:
		z9 = 'We will improve!'

	x10 = df11.iat[9, 0]
	y10 = df12.iat[9, 0]
	if x10 == y10:
		z10 = 'Perfection'
	else:
		z10 = 'We will improve!'

	file1 = './lists/dictation_answers.csv'
	file2 = './lists/words.csv'
	df = pd.read_csv(file1)
	length=df.shape[0]
	for i in range(length):
		df.iat[i, 0] = '-'

	wow = "./lists/web_of_words.csv"
	df_w = pd.read_csv(wow)
	list_wow = []
	list_word = []
	length_w = df_w.shape[0]
	for i in range(length_w):
		list_wow.append(df_w.iat[i, 0])

	for i in range(10):
		rand_word = random.choice(list_wow)
		list_word.append(rand_word)
		list_wow.remove(rand_word)

	dict_word = {'Words': list_word}
	df_word = pd.DataFrame(dict_word)
	df_word.to_csv(file2, mode='w', index=False)

	# df111 = df11.replace(np.nan, '', regex=True)
	# for i in range(10):
	# 	df111.iat[i, 0] = ''

	df11.to_csv(file11, mode = 'w', index=False )

	return render_template("result4.html", x_1=x1, y_1=y1, z_1=z1, x_2=x2, y_2=y2, z_2=z2, x_3=x3, y_3=y3, z_3=z3, x_4=x4, y_4=y4, z_4=z4, x_5=x5, y_5=y5, z_5=z5, x_6=x6, y_6=y6, z_6=z6, x_7=x7, y_7=y7, z_7=z7, x_8=x8, y_8=y8, z_8=z8, x_9=x9, y_9=y9, z_9=z9, x_10=x10, y_10=y10, z_10=z10)


@app.route("/<int:wrd>", methods=["GET", "POST"])
def speak(wrd):
	file1 = "./lists/dictation_answers.csv"
	df = pd.read_csv(file1)
	wo1 = df.iat[0, 0]
	wo2 = df.iat[1, 0]
	wo3 = df.iat[2, 0]
	wo4 = df.iat[3, 0]
	wo5 = df.iat[4, 0]
	wo6 = df.iat[5, 0]
	wo7 = df.iat[6, 0]
	wo8 = df.iat[7, 0]
	wo9 = df.iat[8, 0]
	wo10 = df.iat[9, 0]
	words = pd.read_csv("./lists/words.csv")
	
	# language = 'en'
	# word = str(words.iat[int(wrd), 0])
	# myobj = gTTS(text=word, lang=language, slow=False)
	# myobj.save("welcome.mp3")
	# os.system("mpg123 welcome.mp3")
	return redirect(url_for("listen", w1 = wo1, w2 = wo2, w3 = wo3, w4 = wo4, w5 = wo5, w6 = wo6, w7 = wo7, w8 = wo8, w9 = wo9, w10 = wo10))


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    g=None
    return redirect(url_for('home'))


if __name__ == "__main__":
	app.run(debug=True)
