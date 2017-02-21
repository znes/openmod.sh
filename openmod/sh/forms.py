import wtforms as wtf
import flask_wtf as wtfl

class ComputeForm(wtfl.FlaskForm):
    scn_name = wtf.StringField('scn_name',
                                validators=[wtf.validators.DataRequired()])
    start = wtf.IntegerField('start')
    end = wtf.IntegerField('end')
