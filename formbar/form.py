import logging
import datetime
import sqlalchemy as sa
from formencode import htmlfill
from formbar.renderer import FormRenderer, get_renderer

log = logging.getLogger(__name__)


def get_attributes(cls):
    return [prop.key for prop in sa.orm.class_mapper(cls).iterate_properties
            if isinstance(prop, sa.orm.ColumnProperty)
            or isinstance(prop, sa.orm.RelationshipProperty)]


def get_relations(cls):
    return [prop.key for prop in sa.orm.class_mapper(cls).iterate_properties
            if isinstance(prop, sa.orm.RelationshipProperty)]


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class StateError(Error):
    """Exception raised for state errors while processing the form.

        :msg:  explanation of the error
    """

    def __init__(self, msg):
        self.msg = msg


class Validator(object):
    """Docstring for Validator"""

    def __init__(self, field, error, callback):
        """@todo: to be defined

        :field: @todo
        :error: @todo
        :callback: @todo

        """
        self._field = field
        self._error = error
        self._callback = callback

    def check(self, data):
        return self._callback(self._field, data)


class Form(object):
    """Class for forms. The form will take care for rendering the form,
    validating the submitted data and saving the data back to the
    item.

    The form must be instanciated with an instance of an ``Form``
    configuration and optional an SQLAlchemy mapped item.

    If an SQLAlchemy mapped item is provided there are some basic
    validation is done based on the defintion in the database. Further
    the save method will save the values directly into the database.

    If no item was provided than a dummy item will be created with the
    attributes of the configured fields in the form.
    """

    def __init__(self, config, item=None, dbsession=None, translate=None,
                 change_page_callback={}, renderers={}):
        """Initialize the form with ``Form`` configuration instance and
        optional an SQLAlchemy mapped object.

        :config: FormConfiguration.
        :item: SQLAlchemy mapped instance
        :dbsession: dbsession
        :translate: Translation function which returns a translated
        string for a given msgid
        :set_page_callback: Url which will be called when the user
        changes the currently selected page.
        :renderers: A optional dictionary of custom renderers which are
        provided to the form to render specific form elements. The key
        is the type of the renderer as named in the formular
        configuration.

        """
        self._config = config
        self._item = item
        self._dbsession = dbsession
        if translate:
            self._translate = translate
        else:
            self._translate = lambda msgid: msgid

        self.data = self._serialize(item)
        """After submission this Dictionary will contain either the
        validated data on successfull validation or the origin submitted
        data."""
        self.validated = False
        """Flag to indicate if the form has been validated. Init value
        is False.  which means no validation has been done."""
        self.external_validators = []
        """List with external validators. Will be called an form validation."""
        self.current_page = 0
        """Number of the currently selected page"""
        self.change_page_callback = change_page_callback
        """Dictionary with some parameters used to call an URL when the
        user changes the currently selected page. The dictionary has the
        following keys:
         * url: Name of the URL which will be called
         * item (optional): A string which is send to the URL as GET
           paramenter. Often this is the name of the element (clazzname)
         * itemid (optional): The id of the currently editied element.
        The url will have the additional parameter "page" which holds
        the currently selected page.
        """
        self.external_renderers = renderers
        """Dictionary with external provided custom renderers."""
        self.fields = self._build_fields()
        """Dictionary with fields."""

    def _get_data_from_item(self, item):
        """Returns a dictionary with the values of all attributes and
        relations of the item. The key of the dictionary is the name of
        the attribute/relation.

        :item: Item to get the data from
        :returns: Dictionary with values of the item
        """
        values = {}
        if not item:
            return values
        for key in get_attributes(item.__class__):
            value = getattr(item, key)
            values[key] = value
        return values

    def _serialize(self, item):
        """Returns a dictionary with serialized data from the given
        item. The dictionary will include all attributes and relations
        values of the items. The key in the dictionary is the name of
        the relation/attribute. In case of relations the value in the
        dictionary is the "id" value of the related item.

        :item: Item to serialize
        :returns: Dictionary with serialized values of the item.

        """
        values = self._get_data_from_item(item)
        for key, value in values.iteritems():
            print key, value
            if value is None:
                values[key] = ""
            else:
                try:
                    values[key] = value.id
                except AttributeError:
                    pass
        return values

    def _build_fields(self):
        """Returns a dictionary with all Field instanced which are
        configured for this form.
        :returns: Dictionary with Field instances

        """
        fields = {}
        for name, field in self._config.get_fields().iteritems():
            fields[name] = Field(self, field, self._translate)
        return fields

    def has_errors(self):
        """Returns True if one of the fields in the form has errors"""
        for field in self.fields.values():
            if len(field.get_errors()) > 0:
                return True
        return False

    def get_errors(self):
        """Returns a dictionary of all errors in the form.  This
        dictionary will contain the errors if the validation fails. The
        key of the dictionary is the fieldname of the field.  As a field
        can have more than one error the value is a list."""
        errors = {}
        for field in self.fields.values():
            if len(field.get_errors()) > 0:
                errors[field.name] = field.get_errors()
        return errors

    def get_field(self, name):
        return self.fields[name]

    def add_validator(self, validator):
        return self.external_validators.append(validator)

    def render(self, values={}, page=0):
        """Returns the rendererd form as an HTML string.

        :values: Dictionary with values to be prefilled/overwritten in
        the rendered form.
        :returns: Rendered form.

        """
        self.current_page = page
        renderer = FormRenderer(self, self._translate)
        form = renderer.render(values)
        return htmlfill.render(form, values or self.data)

    def _add_error(self, fieldname, error):
        field = self.get_field(fieldname)
        if isinstance(error, list):
            for err in error:
                field.add_error(err)
        else:
            field.add_error(error)

    def _convert(self, field, value):
        """Returns a converted value depending of the fields datatype

        :field: configuration of the field
        :value: value to be converted
        """
        # Handle missing value. Currently we just return None in case
        # that the provided value is an empty String
        if value == "":
            return None

        dtype = field.type
        if dtype == 'integer':
            try:
                return int(value)
            except ValueError:
                msg = "%s is not a integer value." % value
                self._add_error(field.name, msg)
        elif dtype == 'float':
            try:
                return float(value)
            except ValueError:
                msg = "%s is not a float value." % value
                self._add_error(field.name, msg)
        elif dtype == 'date':
            try:
                #@TODO: Support other dateformats that ISO8601
                y, m, d = value.split('-')
                y = int(y)
                m = int(m)
                d = int(d)
                try:
                    return datetime.date(y, m, d)
                except ValueError, e:
                    msg = "%s is an invalid date (%s)" % (value, e)
                    self._add_error(field.name, msg)
            except:
                msg = "%s is not a valid date format." % value
                self._add_error(field.name, msg)

        print "Converted value %s (%s)" % (value, type(value))
        return value

    def validate(self, submitted):
        """Returns True if the validation succeeds else False.
        Validation of the data happens in three stages:

        1. Prevalidation. Custom rules that are checked before any
        datatype checks on type conversations are made.
        2. Basic type checks and type conversation. Type checks and type
        conversation is done based on the data type of the field and
        further constraint defined in the database if the form is
        instanciated with an SQLAlchemy mapped item.
        3. Postvalidation. Custom rules that are checked after the type
        conversation was done.

        All errors are stored in the errors dictionary through the
        process of validation. After the validation finished the values
        are stored in the data dictionary. In case there has been errors
        the dictionary will contain the origin submitted data.

        :submitted: Dictionary with submitted values.
        :returns: True or False

        """

        # This dictionary will contain the converted data
        values = {}
        # 1. Iterate over all fields and start the validation.
        log.debug('Submitted values: %s' % submitted)
        for fieldname in submitted.keys():
            field = self._config.get_field(fieldname)
            # 3. Prevalidation
            for rule in field.rules:
                if rule.mode != 'pre':
                    continue
                result = rule.evaluate(submitted)
                if not result:
                    self._add_error(fieldname, rule.msg)

            # 4. Basic type conversations, Defaults to String
            # Validation can happen in two variations:
            values[fieldname] = self._convert(field, submitted[fieldname])

            # 5. Postvalidation
            for rule in field.rules:
                if rule.mode != 'post':
                    continue
                result = rule.evaluate(values)
                if not result:
                    self._add_error(fieldname, rule.msg)

        # 6. Custom validation. User defined external validators.
        for validator in self.external_validators:
            if not validator.check(values):
                self._add_error(validator._field, validator._error)

        # If the form is valid. Save the converted and validated data
        # into the data dictionary. If not, than save the origin
        # submitted data.
        has_errors = self.has_errors()
        if not has_errors:
            self.data = values
        else:
            self.data = submitted
        self.validated = True
        return not has_errors

    def save(self):
        """Will save the validated data back into the item. In case of
        an SQLAlchemy mapped item the data will be stored into the
        database.
        :returns: Item with validated data.

        """
        if not self.validated:
            raise StateError('Saving is not possible without prior validation')
        if self.has_errors():
            raise StateError('Saving is not possible if form has errors')

        # Only save if there is actually an item.
        if self._item is not None:
            self._save()

    def _save(self):
        # TODO: Iterate over fields here. Fields should know their value
        # and if they are a relation or not (torsten) <2013-07-24 23:24>

        mapper = sa.orm.object_mapper(self._item)
        relation_properties = filter(
            lambda p: isinstance(p, sa.orm.properties.RelationshipProperty),
            mapper.iterate_properties)
        relation_names = {}
        for prop in relation_properties:
            relation_names[prop.key] = prop

        for key, value in self.data.iteritems():
            if key not in [prop.key for prop in relation_properties]:
                setattr(self._item, key, value)
            else:
                print "relation %s with %s (%s)" % (key, value, type(value))
                db = self._dbsession
                relation = relation_names[key].mapper.class_

                if isinstance(value, list):
                    li = []
                    for val in value:
                        li.append(db.query(relation).filter(relation.id == val.id).one())
                    setattr(self._item, key, li)
                else:
                    if value not in ["[]", None, "None"]:
                        value = db.query(relation).filter(relation.id == value).one()
                    if value == "[]":
                        value = []
                    elif value == "None":
                        value = None
                    setattr(self._item, key, value)


class Field(object):
    """Wrapper for fields in the form. The purpose of this class is to
    provide a common interface for the renderer independent to the
    underlying implementation detail of the field."""

    def __init__(self, form, config, translate):
        """Initialize the field with the given field configuration.

        :config: Field configuration

        """
        self._form = form
        self._config = config
        self.sa_property = self._get_sa_property()
        self._translate = translate
        self.renderer = get_renderer(self, translate)
        self._errors = []

    def __getattr__(self, name):
        """Make attributes from the configuration directly available"""
        return getattr(self._config, name)

    def _get_sa_mapped_class(self):
        # TODO: Raise Exception if this field is not a relation. (None)
        # <2013-07-25 07:44>
        return self.sa_property.mapper.class_

    def _get_sa_property(self):
        if not self._form._item: return None
        mapper = sa.orm.object_mapper(self._form._item)
        for prop in mapper.iterate_properties:
            if prop.key == self.name:
                #print prop.key
                #print prop.__dict__
                return prop

    def get_value(self, default=None):
        return self._form.data.get(self._config.name, default)

    def get_options(self):
        user_defined_options = self._config.options
        if user_defined_options:
            return user_defined_options
        elif self._form._dbsession:
            # Get mapped clazz for the field
            options = []
            clazz = self._get_sa_mapped_class()
            items = self._form._dbsession.query(clazz)
            options.append(("None", ""))
            options.extend([(item, item.id) for item in items])
            return options
        else:
            # TODO: Try to get the session from the item. Ther must be
            # somewhere the already bound session. (torsten) <2013-07-23 00:27>
            log.warning('No db connection configured for this form. Can '
                        'not load options')
            return []

    def add_error(self, error):
        self._errors.append(error)

    def get_errors(self):
        return self._errors

    def render(self):
        """Returns the rendererd HTML for the field"""
        return self.renderer.render()

    def is_relation(self):
        return isinstance(self.sa_property,
                          sa.orm.RelationshipProperty)

    def is_required(self):
        """Returns true if either the required flag of the field
        configuration is set or the formalchemy field is required."""
        # TODO: Try to get the required flag from the underlying
        # datamodel (None) <2013-07-24 21:48>
        #return self.required or self._fa_field.is_required()
        return self.required or False

    def is_readonly(self):
        """Returns true if either the readonly flag of the field
        configuration is set or the formalchemy field is readonly."""
        # TODO: Try to get the required flag from the underlying
        # datamodel (None) <2013-07-24 21:48>
        #return self.readonly or self._fa_field.is_readonly()
        return self.readonly or False
