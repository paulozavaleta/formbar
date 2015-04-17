"""Converters will convert a given value from string to the python value
and vice versa. Converters which will deserialize a string into python
values are named `to_<datatype>` where datatype is the name of the
python data type name. Convertes which serialize the value from python
value into a string are named `from_<datatype>`."""

import logging
import datetime
import re
import sqlalchemy as sa
from babel.dates import format_datetime, format_date
from formbar.helpers import get_local_datetime, get_utc_datetime


log = logging.getLogger(__name__)


def from_timedelta(value):
    """Will return the serialised value for a given timedelta in
    'HH:MM:SS' format."""
    d = datetime.datetime(1, 1, 1) + value
    converted = "%02d:%02d:%02d" % (d.hour,
                                    d.minute, d.second)
    return converted


def to_timedelta(value):
    """Will return a python timedelta for the given value in
    'HH:MM:SS' format. If the value can not be converted and
    exception is raised."""
    if not value:
        return None
    h, m, s = value.split(':')
    h = int(h)
    m = int(m)
    s = int(s)
    converted = datetime.timedelta(hours=h,
                                   minutes=m,
                                   seconds=s)
    return converted


def _split_date(value, locale=None):
    """Will return a tuple integers of YEAR, MONTH, DAY for a given
    date string"""
    #@TODO: Support other dateformats that ISO8601
    if locale == "de":
        d, m, y = value.split('.')
    else:
        y, m, d = value.split('-')
    return int(y), int(m), int(d)


def to_date(value, locale=None):
    """Will return a python date instance for the given value. The format of
    the value depends on the locale setting.

    :value: Datetime as string.
    :locale: Locale setting used to parse the date from the given value.
             Defaults to iso date format (YYYY-mm-DD)
    :returns: Python date instance

    """
    if not value:
        return None
    y, m, d = _split_date(value, locale)
    return datetime.date(y, m, d)


def _split_time(value):
    """Will return a tuple integers of HOUR, MINUTES, SECONDS for a given
    time string"""
    h, M, s = value.split(':')
    return int(h), int(M), int(s)


def to_datetime(value, locale=None):
    """Will return a python datetime instance for the given value. The
    format of the value depends on the locale setting.

    :value: Datetime as string.
    :locale: Locale setting used to parse the date from the given value.
             Defaults to iso date format (YYYY-mm-DD HH:MM:SS)
    :returns: Python datetime instance

    """
    if not value:
        return None
    tmpdate = value.split(' ')
    # Time is optional. If not provided set time to 00:00:00
    if len(tmpdate) == 2:
        date, time = value.split(' ')
    else:
        date = tmpdate[0]
        time = "00:00:00"

    y, m, d = _split_date(date, locale)
    h, M, s = _split_time(time)
    converted = datetime.datetime(y, m, d, h, M, s)
    # Convert datetime to UTC and remove tzinfo because
    # SQLAlchemy fails when trying to store offset-aware
    # datetimes if the date column isn't prepared. As
    # storing dates in UTC is a good idea anyway this is the
    # default.
    converted = get_utc_datetime(converted)
    converted = converted.replace(tzinfo=None)
    return converted


def from_python(field, value):
    """Will return the serialised version of the value the given field
    and value.

    :field: :class:`.Field` instance
    :value: Python value
    :returns: Serialized version.

    """
    serialized = ""
    locale = field._form._locale
    ftype = field.get_type()
    try:
        if value is None:
            serialized = ""
        elif isinstance(value, basestring):
            serialized = value
        elif isinstance(value, list):
            vl = []
            for v in value:
                try:
                    vl.append(v.id)
                except AttributeError:
                    vl.append(v)
            serialized = vl
        else:
            try:
                serialized = value.id
            except AttributeError:
                if ftype == "time":
                    td = datetime.timedelta(seconds=int(value))
                    serialized = from_timedelta(td)
                elif ftype == "interval":
                    serialized = from_timedelta(value)
                elif ftype == "datetime":
                    value = get_local_datetime(value)
                    if locale == "de":
                        dateformat = "dd.MM.yyyy HH:mm:ss"
                    else:
                        dateformat = "yyyy-MM-dd HH:mm:ss"
                    serialized = format_datetime(value, format=dateformat)
                elif ftype == "date":
                    if locale == "de":
                        dateformat = "dd.MM.yyyy"
                    else:
                        dateformat = "yyyy-MM-dd"
                    serialized = format_date(value, format=dateformat)
                else:
                    serialized = value
    except AttributeError:
        log.warning('Can not get value for field "%s". '
                    'The field is no attribute of the item' % field.name)
    return serialized


def to_python(field, value):
    """Will return a instance of a python value of the value the given
    field and value.

    :field: :class:`.Field` instance
    :value: Serialized version of the value
    :returns: Instance of a python type
    """
    relation_names = {}
    try:
        mapper = sa.orm.object_mapper(field._form._item)
        relation_properties = filter(
            lambda p: isinstance(p,
                                 sa.orm.properties.RelationshipProperty),
            mapper.iterate_properties)
        for prop in relation_properties:
            relation_names[prop.key] = prop
    except sa.orm.exc.UnmappedInstanceError:
        if not field._form._item:
            pass  # The form is not mapped to an item.
        else:
            raise

    converted = ""
    dtype = field.get_type()
    if dtype in ['string', 'text']:
        try:
            converted = value
        except ValueError:
            msg = "%s is not a string value." % value
            field._form._add_error(field.name, msg)
    elif dtype == 'integer':
        if not value:
            return None
        try:
            converted = int(value)
        except ValueError:
            msg = "%s is not a integer value." % value
            field._form._add_error(field.name, msg)
    elif dtype == 'float':
        if not value:
            return None
        try:
            converted = float(value)
        except ValueError:
            msg = "%s is not a float value." % value
            field._form._add_error(field.name, msg)
    elif dtype == 'email':
        # TODO: Really check the email. Ask the server mailsserver
        # if the adress is known. (ti) <2014-08-04 16:31>
        if not value:
            return ""
        if not re.match(r"^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$", value):
            msg = "%s is not valid email address." % value
            field._form._add_error(field.name, msg)
        else:
            converted = value
    elif dtype == 'boolean':
        if not value:
            return None
        try:
            converted = value in ['True', '1', 't']
        except ValueError:
            msg = "%s is not a boolean value." % value
            field._form._add_error(field.name, msg)
    elif dtype == 'file':
        try:
            # filename = value.filename
            converted = value.file.read()
        except AttributeError:
            return None
        except ValueError:
            msg = "%s is not a file value." % value
            field._form._add_error(field.name, msg)
    elif dtype == 'date':
        try:
            return to_date(value, field._form._locale)
        except:
            msg = "%s is not a valid date format." % value
            field._form._add_error(field.name, msg)
    elif dtype == 'time':
        try:
            return to_timedelta(value).total_seconds()
        except ValueError:
            msg = "Value '%s' must be in format 'HH:MM:SS'" % value
            field._form._add_error(field.name, msg)
    elif dtype == 'interval':
        try:
            return to_timedelta(value)
        except ValueError:
            msg = "Value '%s' must be in format 'HH:MM:SS'" % value
            field._form._add_error(field.name, msg)
    elif dtype == 'datetime':
        try:
            return to_datetime(value, field._form._locale)
        except:
            log.exception("e")
            msg = "%s is not a valid datetime format." % value
            field._form._add_error(field.name, msg)
    # Reltation handling
    elif dtype == 'manytoone':
        try:
            db = field._form._dbsession
            rel = relation_names[field.name].mapper.class_
            if value in ("", None):
                converted = None
            else:
                value = db.query(rel).filter(rel.id == int(value)).one()
                converted = value
        except ValueError:
            msg = "Reference value '%s' must be of type integer" % value
            field._form._add_error(field.name, msg)
    elif dtype in ['onetomany', 'manytomany']:
        if not value:
            return []

        # In case the there is only one linked item, the value
        # is a string value und not a list. In this case we
        # need to put the value into a list to make the loading
        # and reasinging of items work. Otherwise a item with id
        # 670 will be converted into a list containing 6, 7, 0
        # which will relink different items!
        if not isinstance(value, list):
            value = [value]

        try:
            values = []
            db = field._form._dbsession
            rel = relation_names[field.name].mapper.class_
            for v in [v for v in value if v != ""]:
                values.append(db.query(rel).filter(rel.id == int(v)).one())
            converted = values
        except ValueError:
            msg = "Reference value '%s' must be of type integer" % value
            field._form._add_error(field.name, msg)
    log.debug("Converted value '%s' (%s) of field '%s' (%s)"
              % (converted, type(converted), field.name, dtype))
    return converted
