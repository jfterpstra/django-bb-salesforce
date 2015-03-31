# -*- coding: utf-8 -*-

import time
import csv
from datetime import datetime
from django.utils import timezone
from django.core.management.color import no_style
from django.db import connections
from django.db import transaction
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS, ObjectDoesNotExist
from pytz.exceptions import AmbiguousTimeError
from bb_salesforce.serializers import UnicodeSerializer
from .mappings import IdentityMapping

import logging


logger = logging.getLogger(__name__)


class BaseTransformer(object):

    external_id = 'external_id'

    def get_mapping(self, field):
        """
        Get the mapping object for the specified field from `field_mapping`.
        """
        mapping = self.field_mapping.get(field)

        if mapping == True:
            # True means just copy the field
            mapping = IdentityMapping()

        elif mapping == None:
            # None means: throw away the data
            mapping = NullMapping()

        elif isinstance(mapping, basestring):
            # A string can be passed to map to a different field
            mapping = IdentityMapping(mapping)

        # By this time mapping should be a callable yielding a dict
        assert callable(mapping), u'No forward mapping defined for mapping %s' % mapping

        return mapping

    def transform(self, from_instance):
        value_dict = {}
        for field in self.field_mapping.iterkeys():
            # Get the mapping
            mapping = self.get_mapping(field)
            value_dict.update(mapping(from_instance, field))
        return value_dict


class BaseExporter(object):

    def get_serializer(self, field):
        """
        Get the mapping object for the specified field from `field_mapping`.
        """
        serializer = self.field_mapping.get(field)

        if not serializer:
            # If no string or serializer specified return empty string.
            serializer = EmptySerializer('')
        elif isinstance(serializer, basestring):
            serializer = UnicodeSerializer(serializer)

        # By this time serializer should be a callable yielding a dict
        # assert callable(serializer), u'No forward serializer defined for serializer %s' % serializer
        return serializer


    def export(self, from_instance):

        values = []
        for field in self.field_mapping.iterkeys():
            # Get the mapping
            serializer = self.get_serializer(field)

            values.append(serializer(from_instance))

        return values