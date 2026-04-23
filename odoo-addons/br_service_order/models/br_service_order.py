from odoo import models, fields, api
from odoo.exceptions import UserError

class BrServiceOrder(models.Model):
    _name = 'br.service.order'
    _description = 'Orden de Servicio Botón Rojo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # ── Identificación ──────────────────────────────────────
    name = fields.Char(
        string='Número de orden',
        required=True,
        copy=False,
        readonly=True,
        default='Nuevo',
    )

    # ── Partes involucradas ──────────────────────────────────
    client_id = fields.Many2one(
        'res.partner',
        string='Cliente',
        required=True,
        tracking=True,
    )

    provider_id = fields.Many2one(
        'res.partner',
        string='Proveedor',
        domain=[('br_is_provider', '=', True)],
        tracking=True,
    )

    # ── Detalle del servicio ─────────────────────────────────
    rubro = fields.Selection([
        ('plomero',       'Plomero'),
        ('electricista',  'Electricista'),
        ('limpieza',      'Limpieza'),
        ('jardinero',     'Jardinero'),
        ('piletero',      'Piletero'),
        ('parrillero',    'Parrillero'),
        ('ninyera',       'Niñera'),
        ('lava_autos',    'Lava-autos'),
    ], string='Rubro', required=True, tracking=True)

    service_type = fields.Selection([
        ('directo',     'Directo'),
        ('diagnostico', 'Con Diagnóstico'),
        ('recurrente',  'Recurrente'),
    ], string='Tipo de servicio', default='directo', tracking=True)

    description = fields.Text(
        string='Descripción del trabajo',
    )

    amount = fields.Float(
        string='Monto del servicio',
        digits=(10, 2),
        tracking=True,
    )

    payment_method = fields.Selection([
        ('mp',       'MercadoPago'),
        ('efectivo', 'Efectivo'),
    ], string='Método de pago', default='mp', tracking=True)

    # ── Fecha y franja ───────────────────────────────────────
    scheduled_date = fields.Date(
        string='Fecha programada',
        tracking=True,
    )

    franja = fields.Selection([
        ('manana',  'Mañana (9-12)'),
        ('mediodia','Mediodía (12-15)'),
        ('tarde',   'Tarde (15-18)'),
    ], string='Franja horaria', tracking=True)

    # ── Estado FSM ───────────────────────────────────────────
    state = fields.Selection([
        ('solicitud_creada',    'Solicitud creada'),
        ('pago_autorizado',     'Pago autorizado'),
        ('buscando_proveedor',  'Buscando proveedor'),
        ('proveedor_asignado',  'Proveedor asignado'),
        ('en_camino',           'En camino'),
        ('llego',               'Llegó'),
        ('trabajo_completado',  'Trabajo completado'),
        ('pago_liberado',       'Pago liberado'),
        ('completado',          'Completado'),
        # Estados alternativos
        ('sin_match',           'Sin match'),
        ('cancelado',           'Cancelado'),
        ('disputa_abierta',     'Disputa abierta'),
        ('pendiente_cobro_efvo','Pendiente cobro efectivo'),
    ],
        string='Estado',
        default='solicitud_creada',
        tracking=True,
        readonly=True,
    )

    # ── Fotos ────────────────────────────────────────────────
    photo_before = fields.Binary(string='Foto ANTES')
    photo_after  = fields.Binary(string='Foto DESPUÉS')

    # ── Calificación ─────────────────────────────────────────
    rating = fields.Selection([
        ('1', '⭐'),
        ('2', '⭐⭐'),
        ('3', '⭐⭐⭐'),
        ('4', '⭐⭐⭐⭐'),
        ('5', '⭐⭐⭐⭐⭐'),
    ], string='Calificación del cliente')

    # ── Secuencia automática de número ───────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Si el nombre ya fue asignado (ej. por el endpoint), no sobrescribir
            if vals.get('name') in (None, 'Nuevo', False):
                seq_val = self.env['ir.sequence'].next_by_code('br.service.order')
                vals['name'] = seq_val or 'Nuevo'
        return super().create(vals_list)

    # ── Transiciones de estado ───────────────────────────────
    def action_autorizar_pago(self):
        self.state = 'pago_autorizado'

    def action_buscar_proveedor(self):
        self.state = 'buscando_proveedor'

    def action_asignar_proveedor(self):
        if not self.provider_id:
            raise UserError('Asigná un proveedor antes de continuar.')
        self.state = 'proveedor_asignado'

    def action_en_camino(self):
        self.state = 'en_camino'

    def action_llego(self):
        self.state = 'llego'

    def action_trabajo_completado(self):
        if not self.photo_before:
            raise UserError('El proveedor debe subir la foto ANTES del trabajo.')
        self.state = 'trabajo_completado'

    def action_liberar_pago(self):
        self.state = 'pago_liberado'

    def action_completar(self):
        self.state = 'completado'

    def action_cancelar(self):
        self.state = 'cancelado'

    def action_abrir_disputa(self):
        self.state = 'disputa_abierta'

    def action_sin_match(self):
        self.state = 'sin_match'