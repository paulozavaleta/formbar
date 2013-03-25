import os
import datetime
import unittest

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine('sqlite:///:memory:', echo=False)
Session = scoped_session(sessionmaker())
Session.configure(bind=engine)
Base = declarative_base()

from formbar import test_dir
from formbar.config import load, Config
from formbar.form import Form, StateError


RESULT = """<div class="formbar-form"><form id="customform" class="testcss" method="GET" action="http://" autocomplete="off" >    \n        <div class="row-fluid"><tr>\n      \n        \n        <div class="span12">\n      \n        \n        <label for="string">\n  String field\n</label>\n\n  <div class="readonlyfield">\n    &nbsp;\n  </div>\n\n\n\n\n        </div>\n\n        </div>\n        \n          \n        \n        <div class="row-fluid"><tr>\n      \n        \n        <div class="span12">\n      \n        \n        <label for="default">\n  Default\n</label>\n\n  <div class="readonlyfield">\n    &nbsp;\n  </div>\n\n\n\n\n        </div>\n\n        </div>\n        <div class="row-fluid"><tr>\n      \n        \n        <div class="span6">\n      \n        \n        <label for="float">\n  Float field\n</label>\n\n  <div class="readonlyfield">\n    &nbsp;\n  </div>\n\n\n<div class="text-help">\n  <i class="icon-info-sign"></i>\n  This is is a very long helptext which should span over\n      multiple rows. Further the will check if there are further html\n      tags allowed.\n</div>\n\n\n        </div>\n        \n        <div class="span6">\n      \n        \n        <label for="date">\n    <sup>(1)</sup>\n  Date field\n</label>\n\n  <div class="readonlyfield">\n    &nbsp;\n  </div>\n\n\n<div class="text-help">\n  <i class="icon-info-sign"></i>\n  This is my helptext\n</div>\n\n\n        </div>\n\n        </div>\n        \n          \n        \n        <div class="row-fluid"><tr>\n      \n        \n        <div class="span6">\n      \n        \n        <label for="string">\n  String field\n</label>\n\n  <div class="readonlyfield">\n    &nbsp;\n  </div>\n\n\n\n\n        </div>\n        \n        <div class="span6">\n      \n        \n        <label for="integer">\n  Integer field\n    <a href="#" data-toggle="tooltip" class="formbar-tooltip" data-original-title="Required fa_field"><i class="icon-asterisk"></i></a>\n</label>\n\n  <div class="readonlyfield">\n    &nbsp;\n  </div>\n\n\n\n\n        </div>\n\n        </div>\n\n\n\n\n\n<script>\n  $(\'.formbar-tooltip\').tooltip();\n</script>\n<div class="row-fluid"><div class="span12 button-pane well-small"><button type="submit" class="btn btn-primary">Submit</button><button type="reset" class="btn btn-warning">Reset</button></div></div></form></div>"""


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    fullname = Column(String)
    password = Column(Integer)

    def __init__(self, name=None, fullname=None, password=None):
        self.name = name
        self.fullname = fullname
        self.password = password

    def __repr__(self):
        return "<User('%s','%s', '%s')>" % (self.name, self.fullname,
                                            self.password)


class TestFormValidation(unittest.TestCase):

    def setUp(self):
        tree = load(os.path.join(test_dir, 'form.xml'))
        config = Config(tree)
        form_config = config.get_form('customform')
        self.form = Form(form_config)

    def test_form_init(self):
        pass

    def test_form_unknown_field(self):
        values = {'unknown': 'test', 'integer': '15', 'date': '1998-02-01'}
        # Not raising error anymore, now just take the value in the
        # unknown field.
        #self.assertRaises(KeyError, self.form.validate, values)
        self.form.validate(values)
        self.assertEqual(self.form.data['unknown'], 'test')

    def test_form_validate_fail(self):
        values = {'default': 'test', 'integer': '15', 'date': '1998-02-01'}
        self.assertEqual(self.form.validate(values), False)

    def test_form_validate_fail_checkvalues(self):
        values = {'default': 'test', 'integer': '15', 'date': '1998-02-01'}
        self.assertEqual(self.form.validate(values), False)
        self.assertEqual(self.form.data['integer'], '15')
        self.assertEqual(self.form.data['date'], '1998-02-01')

    def test_form_validate_ok(self):
        values = {'default': 'test', 'integer': '16', 'date': '1998-02-01'}
        self.assertEqual(self.form.validate(values), True)

    def test_form_deserialize_int(self):
        values = {'default': 'test', 'integer': '16', 'date': '1998-02-01'}
        self.form.validate(values)
        self.assertEqual(self.form.data['integer'], 16)

    def test_form_deserialize_float(self):
        values = {'default': 'test', 'integer': '16',
                  'date': '1998-02-01', 'float': '87.5'}
        self.assertEqual(self.form.validate(values), True)
        self.assertEqual(self.form.data['float'], 87.5)

    def test_form_deserialize_date(self):
        values = {'default': 'test', 'integer': '16',
                  'float': '87.5', 'date': '1998-02-01'}
        self.form.validate(values)
        self.assertEqual(self.form.data['date'], datetime.date(1998, 2, 1))

    def test_form_deserialize_string(self):
        values = {'default': 'test', 'integer': '16', 'date': '1998-02-01'}
        self.form.validate(values)
        self.assertEqual(self.form.data['default'], 'test')

    def test_form_save(self):
        values = {'default': 'test', 'integer': '16', 'date': '1998-02-01'}
        self.assertEqual(self.form.validate(values), True)

    def test_form_save_without_validation(self):
        self.assertRaises(StateError, self.form.save)

    def test_form_fields(self):
        self.assertEqual(len(self.form.fields.values()), 5)


class TestFormRenderer(unittest.TestCase):

    def setUp(self):
        tree = load(os.path.join(test_dir, 'form.xml'))
        config = Config(tree)
        form_config = config.get_form('customform')
        self.form = Form(form_config)

    def test_form_render(self):
        html = self.form.render()
        self.assertEqual(html, RESULT)


class TestFormAlchemyForm(unittest.TestCase):

    def _insert_item(self):
        item = User('ed', 'Ed Jones', 'edspassword')
        self.session.add(item)
        self.session.commit()
        return item

    def setUp(self):
        Base.metadata.create_all(engine)
        tree = load(os.path.join(test_dir, 'form.xml'))
        self.config = Config(tree)
        self.session = Session()

    def tearDown(self):
        Session.remove()

    def test_read(self):
        form_config = self.config.get_form('userform1')
        item = self._insert_item()
        form = Form(form_config, item)
        self.assertEqual(len(form.fs.render_fields), 2)

    def test_create(self):
        form_config = self.config.get_form('userform2')
        item = User()
        form = Form(form_config, item)
        self.assertEqual(len(form.fs.render_fields), 3)

    def test_create_save(self):
        form_config = self.config.get_form('userform2')
        item = User()
        # Important! Provide the dbsession if you want to create a new
        # item
        form = Form(form_config, item, self.session)
        values = {"name": "paulpaulpaul", "fullname": "Paul Wright",
                  "password": "1"}
        if form.validate(values):
            saved_item = form.save()
            self.assertEqual(saved_item, item)
        result = self.session.query(User).all()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "paulpaulpaul")

    def test_edit_save(self):
        form_config = self.config.get_form('userform2')
        item = self._insert_item()
        item = self._insert_item()
        result = self.session.query(User).all()
        form = Form(form_config, item)
        result = self.session.query(User).all()
        values = {"name": "paulpaulpaul", "fullname": "Paul Wright",
                  "password": "1"}
        if form.validate(values):
            form.save()
        result = self.session.query(User).all()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "ed")
        self.assertEqual(result[1].name, "paulpaulpaul")


if __name__ == '__main__':
    unittest.main()