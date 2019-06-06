"""
.. module:: forms
   :platform: Unix
   :synopsis: Contains the forms

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

from django import forms

class ContactForm(forms.Form):
	name = forms.CharField(label='Your name', max_length=255)
	email = forms.EmailField(label='Your email')
	subject = forms.CharField(label='Subject', max_length=255)
	body = forms.CharField(label='Your message', widget=forms.Textarea)