# Copyright 2020 Mikel Arregi Etxaniz - AvanzOSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, models
from odoo.tools.safe_eval import safe_eval
from odoo.models import expression


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    @api.multi
    def _create_serial_lot(self, suffix):
        return self.env['stock.production.lot'].create(
            {'name': "{}-{}".format(self.production_id.name, suffix),
             'product_id': self.production_id.product_id.id})

    @api.multi
    def button_execute_all_moves(self):
        for order in self:
            lot_incremental = 0
            while (order.qty_production != order.qty_produced or
                   order.state != 'done'):
                lot_incremental += 1
                serial_lot = order._create_serial_lot(lot_incremental)
                order.final_lot_id = serial_lot
                order.record_production()

    @api.multi
    def button_open_active_move_lines(self):
        self.ensure_one()
        self = self.with_context(
            default_workorder_id=self.id)
        action = self.env.ref('stock.stock_move_line_action')
        action_dict = action.read()[0] if action else {}
        action_dict['context'] = safe_eval(
            action_dict.get('context', '{}'))
        action_dict['context'].pop('search_default_done', False)
        action_dict['context'].pop('search_default_groupby_product_id', False)
        action_dict['context'].update({
            'default_workorder_id': self.id,
            'search_default_groupby_lot_produced_id': 1,
        })
        domain = expression.AND([
            [('workorder_id', '=', self.id)],
            safe_eval(action.domain or '[]')])
        action_dict.update({'domain': domain})
        return action_dict

    def button_open_lots(self):
        self.ensure_one()
        location_obj = self.env['stock.location']
        physical_location = location_obj.search(
            [('name', '=', 'Physical Locations')])
        virtual_location = location_obj.search(
                    [('name', '=', 'Virtual Locations')])
        move_lines = self.active_move_line_ids | self.move_line_ids
        produce_lines = move_lines.filtered(
            lambda x: x.location_id._has_parent(virtual_location) and
            x.location_dest_id._has_parent(physical_location))
        produce_lots = produce_lines.mapped('lot_id')
        action = self.env.ref('stock.action_production_lot_form')
        action_dict = action.read()[0] if action else {}
        action_dict['context'] = safe_eval(
            action_dict.get('context', '{}'))
        action_dict['context'].pop('search_default_group_by_product', False)
        action_dict['context'].update({
            'default_workorder_id': self.id,
        })
        action_dict['ids'] = produce_lots
        domain = expression.AND([
            [('id', 'in', produce_lots.ids)],
            safe_eval(action.domain or '[]')])
        action_dict.update({'domain': domain})
        return action_dict