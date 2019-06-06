from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import tourf.routing

application = ProtocolTypeRouter({
	'websocket': AuthMiddlewareStack(
		URLRouter(tourf.routing.websocket_urlpatterns)
	),
})
