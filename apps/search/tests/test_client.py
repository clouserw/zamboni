import socket

from django.utils import translation
from django.conf import settings

import mock
from nose.tools import eq_, assert_raises
from pyquery import PyQuery as pq

import amo
import amo.tests
from addons.models import Addon
from amo.urlresolvers import reverse
from bandwagon.models import Collection
from search.client import (extract_from_query, get_category_id,
                           Client as SearchClient, CollectionsClient,
                           PersonasClient, SearchError, )


def test_extract_from_query():
    """Test that the correct terms are extracted from query strings."""

    eq_(("yslow ", "3.4",),
        extract_from_query("yslow voo:3.4", "voo", "[0-9.]+"))


class GetCategoryIdTest(amo.tests.TestCase):
    fixtures = ["base/category"]

    def test_get_category_id(self):
        """Tests that we get the expected category ids"""
        eq_(get_category_id('feeds', amo.FIREFOX.id), 1)


query = lambda *args, **kwargs: SearchClient().query(*args, **kwargs)


class SearchDownTest(amo.tests.TestCase):

    def test_search_down(self):
        """
        Test that we raise a SearchError if search is not running.
        """
        self.assertRaises(SearchError, query, "")

    def test_collections_search_down(self):
        self.client.get('/')
        resp = self.client.get(reverse('search.search') + '?cat=collections')
        doc = pq(resp.content)
        eq_(doc('.no-results').length, 1)

    def test_personas_search_down(self):
        self.client.get('/')
        resp = self.client.get(reverse('search.search') + '?cat=personas')
        doc = pq(resp.content)
        eq_(doc('.no-results').length, 1)


class BadSortOptionTest(amo.tests.TestCase):
    def test_bad_sort_option(self):
        """Test that we raise an error on bad sort options."""
        assert_raises(SearchError, lambda: query('xxx', sort="upsidedown"))


