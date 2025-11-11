"""
Lightweight mock database utilities for Django tests without touching a real DB.

Usage (unittest):

    from django.test import SimpleTestCase
    from tests.mockdb.patcher import MockDB

    class MyViewTests(SimpleTestCase):
        def setUp(self):
            self.mockdb = MockDB()
            self.mockdb.apply()

        def tearDown(self):
            self.mockdb.restore()

"""
