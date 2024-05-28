#!/usr/bin/python

"""
Bank accounts.
"""

__copyright__ = 'Copyright (c) 2014 Emanuele Pucciarelli, C.O.R.P. s.n.c.'
__license__ = '3-clause BSD'

from .util import AttributeCarrier
from lxml import etree


class MissingCUCError(Exception):
    """
    Raised when an Entity without a `cuc` attribute is used as an initiator.
    """
    pass


class AddressFormatError(Exception):
    """
    Raised when an Address is created with unsuitable arguments.
    """


class Address(AttributeCarrier):
    """
    The postal address of an entity.
    """
    def __init__(self, address=None, country=None, town=None, *args):
        """
        The argument processing is NOT based on keyword parameters, so we
        cannot inherit from AttributeCarrier.
        """
        # pylint: disable=super-init-not-called
        self.lines = address
        self.country = country
        self.town = town

    def perform_checks(self):
        "Check the length of each line."
        if self.lines is not None:
            if not isinstance(self.lines, (list, tuple)):
                raise AddressFormatError('Address format error')
            line_count = len(self.lines)
            if line_count < 1 or line_count > 2:
                raise AddressFormatError('Must have either 1 or 2 address lines')
            for line in self.lines:
                if len(line) < 1 or len(line) > 70:
                    raise AddressFormatError('Line must have length '
                                            'between 1 and 70 characters')

    def emit_tag(self):
        "Emit the postal address with each of its lines."
        root = etree.Element('PstlAdr')
        if self.town is not None:
            etree.SubElement(root, 'TwnNm').text = self.town
        if self.country is not None:
            etree.SubElement(root, 'Ctry').text = self.country
        if self.lines is not None:
            for line in self.lines:
                etree.SubElement(root, 'AdrLine').text = line
        return root


def emit_id_tag(id_code, id_type=None):
    'Emit a single ID subtree, with root <Othr>.'
    othr = etree.Element('Othr')
    id_tag = etree.SubElement(othr, 'Id')
    id_tag.text = id_code
    if id_type is not None:
        issuer = etree.SubElement(othr, 'Issr')
        issuer.text = id_type
    return othr


class IdHolder(AttributeCarrier):
    # pylint: disable=no-member
    """
    Describes an Initiator.
    Must have a CUC; may have an Italian tax code.
    """
    allowed_args = ('name', 'cf', 'code', 'private', 'cuc', 'address',
                    'country', 'pstl_town', 'pstl_country', 'sia_code')

    def __init__(self, **kwargs):
        self.private = False
        self.pstl = None
        super(IdHolder, self).__init__(**kwargs)

    def perform_checks(self):
        # pylint: disable=access-member-before-definition
        # pylint: disable=attribute-defined-outside-init
        "Check argument lengths."
        if hasattr(self, 'name'):
            self.max_length('name', 70)
        if hasattr(self, 'cf'):
            assert not hasattr(self, 'code')
            self.max_length('cf', 16)
        if hasattr(self, 'cuc'):
            self.max_length('cuc', 35)
        if hasattr(self, 'pstl_country'):
            self.length('pstl_country', 2)
        if hasattr(self, 'pstl_town'):
            self.max_length('pstl_town', 35)
        if hasattr(self, 'country'):
            self.length('country', 2)
        if hasattr(self, 'pstl_country') or hasattr(self, 'pstl_country'):
            pstl_country = None
            pstl_town = None
            address = None
            if hasattr(self, 'pstl_country'):
                pstl_country = self.pstl_country
            if hasattr(self, 'pstl_town'):
                pstl_town = self.pstl_town
            if hasattr(self, 'address'):
                address = self.address

            self.pstl = Address(address, pstl_country,
                                pstl_town)
            assert isinstance(self.pstl, Address)

    def emit_tag(self, tag=None, as_initiator=False, hide=False):
        """
        Emit a subtree for an entity, using the supplied tag for the root
        element. If the identity is the Initiator's, emit the CUC as well.
        """
        if as_initiator:
            tag = 'InitgPty'
        root = etree.Element(tag)

        # Name
        if hasattr(self, 'name'):
            name = etree.SubElement(root, 'Nm')
            name.text = self.name

        # Address
        if self.pstl is not None and not as_initiator:
            root.append(self.pstl.__tag__())

        # ID
        idtag = etree.SubElement(root, 'Id')
        if self.private:
            id_container = 'PrvtId'
        else:
            id_container = 'OrgId'
        orgid = etree.SubElement(idtag, id_container)

        # CUC
        if as_initiator or hide:
            if not hasattr(self, 'cuc'):
                raise MissingCUCError
            orgid.append(emit_id_tag(self.cuc, 'CBI'))

        # Tax code
        if not hide:
            if hasattr(self, 'cf'):
                orgid.append(emit_id_tag(self.cf, 'ADE'))

        if hasattr(self, 'code'):
            orgid.append(emit_id_tag(self.code, None))

        if not as_initiator and hasattr(self, 'country'):
            etree.SubElement(root, 'CtryOfRes').text = self.country

        return root
