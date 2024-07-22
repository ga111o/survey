from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import markdown

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///surveys.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    questions = db.relationship('Question', backref='survey', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    markdown_text = db.Column(db.Text, nullable=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    comment = db.Column(db.String(500), nullable=True)
    responses = db.relationship('Response', backref='question', lazy=True)
    likert_scales = db.relationship('LikertScale', backref='question', lazy=True)  # 추가된 부분

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer = db.Column(db.String(500), nullable=False)
    comment = db.Column(db.String(500), nullable=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)  

class LikertScale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    scale_text = db.Column(db.String(100), nullable=False)


with app.app_context():
    db.create_all()

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        questions = request.form.getlist('questions')
        comments = request.form.getlist('comments')
        markdowns = request.form.getlist('markdowns')
        likert_scales = request.form.getlist('likert_scales')

        survey = Survey(title=title)
        db.session.add(survey)
        db.session.commit()

        for question_text, comment, markdown, likert_scale in zip(questions, comments, markdowns, likert_scales):
            question = Question(text=question_text, survey_id=survey.id, comment=comment, markdown_text=markdown)
            db.session.add(question)
            db.session.commit()

            if likert_scale:
                for scale_text in likert_scale.split(','):
                    likert = LikertScale(question_id=question.id, scale_text=scale_text.strip())
                    db.session.add(likert)

        db.session.commit()
        return redirect(url_for('survey_list'))
    return render_template('create.html')


@app.route('/survey/<int:session_id>', methods=['GET'])
def session_survey_list(session_id):
    surveys = Survey.query.all()
    user_responses = Response.query.filter_by(session_id=session_id).all()
    participated_survey_ids = {response.question.survey_id for response in user_responses}
    return render_template('survey.html', surveys=surveys, session_id=session_id, participated_survey_ids=participated_survey_ids)


@app.route('/survey/<int:session_id>/<int:survey_id>', methods=['GET', 'POST'])
def take_survey(session_id, survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if request.method == 'POST':
        for question in survey.questions:
            answer = request.form.get(str(question.id))
            if answer:
                # LikertScale의 scale_text를 가져오는 부분 추가
                likert_scale = LikertScale.query.filter_by(question_id=question.id, id=answer).first()
                if likert_scale:
                    response = Response(
                        question_id=question.id,
                        answer=likert_scale.scale_text,  # scale_text 저장
                        session_id=session_id,
                        comment=question.comment  
                    )
                    db.session.add(response)

        db.session.commit()
        return redirect(url_for('session_survey_list', session_id=session_id))
    return render_template('take_survey.html', survey=survey, session_id=session_id)


@app.route('/survey/<int:survey_id>/edit', methods=['GET', 'POST'])
def edit_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    if request.method == 'POST':
        survey.title = request.form['title']
        questions = request.form.getlist('questions')
        comments = request.form.getlist('comments')
        markdowns = request.form.getlist('markdowns')
        likert_scales = request.form.getlist('likert_scales')

        # 기존 질문과 리커트 스케일을 삭제
        Question.query.filter_by(survey_id=survey.id).delete(synchronize_session='fetch')
        LikertScale.query.filter(LikertScale.question_id.in_([q.id for q in survey.questions])).delete(synchronize_session='fetch')

        # 새 질문과 리커트 스케일 추가
        for question_text, comment, markdown, likert_scale in zip(questions, comments, markdowns, likert_scales):
            if markdown:  
                question_text = question_text or " "
            if question_text:
                question = Question(text=question_text, survey_id=survey.id, comment=comment, markdown_text=markdown)
                db.session.add(question)

                # 리커트 스케일 추가
                if likert_scale:
                    for scale_text in likert_scale.split(','):
                        likert = LikertScale(question_id=question.id, scale_text=scale_text.strip())
                        db.session.add(likert)

        db.session.commit()
        return redirect(url_for('survey_list'))
    return render_template('edit_survey.html', survey=survey)


@app.route('/survey/<int:survey_id>/delete', methods=['POST'])
def delete_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    db.session.delete(survey)
    db.session.commit()
    return redirect(url_for('survey_list'))

@app.route('/start', methods=['GET', 'POST'])
def start():
    if request.method == 'POST':
        session_id = request.form['session_id']
        return redirect(url_for('session_survey_list', session_id=session_id))
    return render_template('start.html')

@app.template_filter('markdown')
def markdown_filter(text):
    return markdown.markdown(text)

if __name__ == '__main__':
    app.run(debug=True)
