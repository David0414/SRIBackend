from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
CORS(app)

# Clave de API de OpenRouteService
ORS_API_KEY = os.getenv('ORS_API_KEY')

@app.route('/route', methods=['POST'])
def route():
    data = request.get_json()
    try:
        waypoints = [coord[::-1] for coord in data['waypoints']]  # Convierte [lat, lng] → [lng, lat]
        obstacles = data.get('obstacles', [])

        print(f"📍 Ruta con {len(waypoints)} puntos y {len(obstacles)} bloqueos")

        avoid_polygons = {
            "type": "MultiPolygon",
            "coordinates": [
                [[
                    [lng - 0.00015, lat - 0.00015],
                    [lng - 0.00015, lat + 0.00015],
                    [lng + 0.00015, lat + 0.00015],
                    [lng + 0.00015, lat - 0.00015],
                    [lng - 0.00015, lat - 0.00015]
                ]] for lat, lng in obstacles
            ]
        } if obstacles else None

        # Payload básico
        payload = {
            'coordinates': waypoints,
            'instructions': False
        }

        # Solo agregar rutas alternativas si hay exactamente dos puntos (start y end)
        if len(waypoints) == 2:
            payload['alternative_routes'] = {
                'share_factor': 0.6,
                'target_count': 3
            }

        if avoid_polygons:
            payload['options'] = {'avoid_polygons': avoid_polygons}

        response = requests.post(
            'https://api.openrouteservice.org/v2/directions/driving-car/geojson',
            headers={
                'Authorization': ORS_API_KEY,
                'Content-Type': 'application/json'
            },
            json=payload
        )

        if response.status_code != 200:
            print("❌ ORS rechazó la solicitud:", response.json())
            return jsonify({'error': 'ORS rechazó la solicitud'}), 400

        route_data = response.json()
        rutas = [
            [coord[::-1] for coord in feature['geometry']['coordinates']]
            for feature in route_data.get('features', [])
        ]

        summary = route_data['features'][0]['properties']['summary']
        distancia = round(summary['distance'], 1)
        duracion = round(summary['duration'] / 60, 2)

        print(f"✅ Ruta generada: {distancia} m, {duracion} min")

        return jsonify({
            'routes': rutas,
            'distancia': distancia,
            'duracion': duracion
        })

    except Exception as e:
        print(f"❌ Error en /route: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/nearest-node', methods=['POST'])
def nearest_node():
    return jsonify({'distance': 0})

# Para desarrollo local
if __name__ == "__main__":
    env = os.getenv("FLASK_ENV", "development")
    if env == "development":
        app.run(host="0.0.0.0", port=5000, debug=True)