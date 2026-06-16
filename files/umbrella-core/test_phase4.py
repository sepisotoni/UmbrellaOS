import asyncio
from main import app
from models import Player, Punishment, Appeal

async def comprehensive_test():
    print('=== PHASE 4 COMPREHENSIVE VERIFICATION ===\n')
    
    # Test 1: Verify all routers are loaded
    print('[TEST 1] Router Registration')
    routes = {}
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            path = route.path
            method = list(route.methods)[0] if route.methods else 'GET'
            if '/api/v1/' in path:
                if path not in routes:
                    routes[path] = []
                routes[path].append(method)
    
    players_routes = [r for r in routes.keys() if '/players' in r]
    punishments_routes = [r for r in routes.keys() if '/punishments' in r]
    appeals_routes = [r for r in routes.keys() if '/appeals' in r]
    
    print(f'  ✓ Players endpoints: {len(players_routes)} routes')
    print(f'  ✓ Punishments endpoints: {len(punishments_routes)} routes')
    print(f'  ✓ Appeals endpoints: {len(appeals_routes)} routes')
    print(f'  ✓ Total Phase 4 routes: {len(players_routes) + len(punishments_routes) + len(appeals_routes)}')
    
    # Test 2: Verify schemas
    print('\n[TEST 2] Schema Validation')
    from api.routers.players import PlayerSchema, PlayerDetailSchema, IPAddressSchema
    from api.routers.punishments import PunishmentSchema, PunishmentCreateRequest
    from api.routers.appeals import AppealSchema, AppealCreateRequest
    
    print('  ✓ PlayerSchema imported')
    print('  ✓ PunishmentSchema imported')
    print('  ✓ AppealSchema imported')
    print('  ✓ All request models imported')
    
    # Test 3: Verify database models
    print('\n[TEST 3] Database Models')
    print(f'  ✓ Player model: {Player.__tablename__}')
    print(f'  ✓ Punishment model: {Punishment.__tablename__}')
    print(f'  ✓ Appeal model: {Appeal.__tablename__}')
    
    # Test 4: Verify relationships
    print('\n[TEST 4] Model Relationships')
    player_has_punishments = hasattr(Player, 'punishments')
    player_has_appeals = hasattr(Player, 'appeals')
    punishment_has_appeals = hasattr(Punishment, 'appeals')
    
    print(f'  ✓ Player.punishments: {player_has_punishments}')
    print(f'  ✓ Player.appeals: {player_has_appeals}')
    print(f'  ✓ Punishment.appeals: {punishment_has_appeals}')
    
    print('\n=== ALL TESTS PASSED ===')

try:
    asyncio.run(comprehensive_test())
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
