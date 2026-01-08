from odoo import models, fields

class RentalProperty(models.Model):
    _inherit = 'product.template'

    max_guests = fields.Integer('Max Guests')
    beds = fields.Integer('Beds')
    bedrooms = fields.Integer('Bedrooms')
    bathrooms = fields.Integer('Bathrooms')
    street = fields.Char('Street')
    number = fields.Char('Number')
    postal_code = fields.Char('Postal Code')
    toilet_grab_bar_available = fields.Boolean('Toilet Grab Bar')

    # Amenity fields
    air_conditioning_available = fields.Boolean('Air Conditioning')
    terrace_available = fields.Boolean('Terrace')
    garden_available = fields.Boolean('Garden')
    pool_available = fields.Boolean('Pool')
    hot_tub_available = fields.Boolean('Hot Tub')
    ev_charger_available = fields.Boolean('EV Charger')
    indoor_fireplace_available = fields.Boolean('Indoor Fireplace')
    outdoor_fireplace_available = fields.Boolean('Outdoor Fireplace')
    dedicated_workspace_available = fields.Boolean('Dedicated Workspace')
    gym_available = fields.Boolean('Gym')

    # Accessibility fields
    shower_grab_bar_available = fields.Boolean('Shower Grab Bar')
    step_free_shower_available = fields.Boolean('Step-Free Shower')
    shower_bath_chair_available = fields.Boolean('Shower Bath Chair')
    step_free_bedroom_access_available = fields.Boolean('Step-Free Bedroom Access')
    wide_bedroom_entrance_available = fields.Boolean('Wide Bedroom Entrance')
    step_free_access_available = fields.Boolean('Step-Free Access')
