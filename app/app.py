#pip install folium
#pip install pywebview[GTK]



import os
import folium
from folium.plugins import HeatMap
import csv
import mysql.connector
import webview
from datetime import datetime

DATABASE1 = 'team404.sql'
# Database configuration
DATABASE = {
    'host': 'localhost',
    'port': 3306,
    'database': 'team404',
    'user': 'team404user',
    'password': 'pass',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}


def get_connection():
    """Return a new database connection."""
    return mysql.connector.connect(**DATABASE) 

class HeatmapGenerator:
    def __init__(self, data_file='data.csv'):
        self.data_file = data_file


    def read_data(self):
        """Reads data from the CSV file and returns a list of heat data."""
        heat_data = []
        if not os.path.exists(self.data_file):
            print("Data file does not exist!")
            return heat_data

        with open(self.data_file, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    lat = float(row['latitude'])
                    lon = float(row['longitude'])
                    strength = float(row['signal_strength'])
                    heat_data.append([lat, lon, strength])
                except ValueError:
                    continue  # Ignore rows with invalid data
        return heat_data

    def create_heatmap(self, output_file='heatmap_output.html'):
        """Generates a heatmap and saves it to an HTML file."""
        data = self.read_data()
        if not data:
            print("No valid data found!")
            return None

        # Calculate the average latitude and longitude for centering the map
        avg_lat = sum(d[0] for d in data) / len(data)
        avg_lon = sum(d[1] for d in data) / len(data)

        # Create a Folium map centered on the average lat/lon
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=19)

        # Prepare data for the heatmap, adjusting signal strength for visibility
        norm_data = [[d[0], d[1], max(0, 100 + d[2])] for d in data]

        # Add heatmap to the map
        HeatMap(norm_data).add_to(m)

        # Save the map to the output file
        m.save(output_file)
        return output_file

class HeatmapApp:

    def generate_external_heatmap_from_sql(self):
        """Generates a heatmap using gpsLat, gpsLong, and strength from the SQL DB."""
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT gpsLat, gpsLong, strength
        FROM IngestDB
        WHERE gpsLat IS NOT NULL AND gpsLong IS NOT NULL;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {"success": False, "message": "No GPS data found."}

        heat_data = []
        for row in rows:
            try:
                lat = float(row[0])
                lon = float(row[1])
                strength = float(row[2])
                heat_data.append([lat, lon, max(0, 100 + strength)])  # normalize
            except (TypeError, ValueError):
                continue

        if not heat_data:
            return {"success": False, "message": "No valid GPS data available."}

        avg_lat = sum(d[0] for d in heat_data) / len(heat_data)
        avg_lon = sum(d[1] for d in heat_data) / len(heat_data)

        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=19)
        HeatMap(heat_data).add_to(m)

        output_file = 'external_heatmap.html'
        m.save(output_file)

        return {"success": True, "file": output_file}



    def __init__(self):
        self.generator = HeatmapGenerator()
        self.wifi_data = self.read_wifi_data()


    def run(self):
        """Run the app and initialize the first heatmap."""
        # Create the initial heatmap
        self.generator.create_heatmap()

        # Start the PyWebView window
        html_path = os.path.join(os.path.dirname(__file__), 'index.html')
        webview.create_window('Heatmap Application', f"file://{html_path}", js_api=self)
        webview.start(debug=True)

    def generate_new_heatmap(self):
        """Regenerate the heatmap."""
        self.generator.create_heatmap()
        print("Heatmap regenerated!")

    

    def on_wifi_click(self, ssid):
        """Return full analytics data for selected SSID from SQL database."""
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT ID, projectID, captureTime, srcMac, dstMac, SSID, encType,
            authMode, gpsLat, gpsLong, strength, contentLength,
            typeExternal, typeInternal, srcIP, dstIP, srcPort,
            dstPort, sniffType
        FROM IngestDB
        WHERE SSID = %s
        ORDER BY captureTime DESC
        LIMIT 1;
        """
        cursor.execute(query, (ssid,))
        rows = cursor.fetchall()
        conn.close()

        # Column names must match the SELECT statement
        column_names = [
            "ID", "projectID", "captureTime", "srcMac", "dstMac", "SSID", "encType",
            "authMode", "gpsLat", "gpsLong", "strength", "contentLength",
            "typeExternal", "typeInternal", "srcIP", "dstIP", "srcPort",
            "dstPort", "sniffType"
        ]

        result = []
        for row in rows:
            record = dict(zip(column_names, row))

            # Convert datetime to string (ISO format)
            if isinstance(record["captureTime"], datetime):
                record["captureTime"] = record["captureTime"].isoformat()

            result.append(record)

        return result



    def read_wifi_data(self):
        """Fetch Wi-Fi data from SQL database."""
        conn = get_connection()
        cursor = conn.cursor()

        # Modify the query to match your table structure
        query = """
            SELECT 
                ssid,
                COUNT(*) AS ssid_count
            FROM IngestDB
            WHERE projectID = (
                SELECT MAX(projectID) FROM IngestDB
            )
            GROUP BY ssid
            ORDER BY ssid_count DESC;
        """
        cursor.execute(query)
        wifi_data = cursor.fetchall()
        print(wifi_data)

        conn.close()

        # Map the fetched data into a list of dictionaries
        wifi_data_dict = [
            {"ssid": row[0], "strength": row[1]}
            for row in wifi_data
        ]
        print("Fetched WiFi Data:", wifi_data_dict)
        return wifi_data_dict
    
    def read_wifi_dataInternal(self):
        """Fetch Wi-Fi data from SQL database."""
        conn = get_connection()
        cursor = conn.cursor()

        # Modify the query to match your table structure
        query = """
            SELECT 
                ssid,
                COUNT(*) AS ssid_count
            FROM IngestDB
            WHERE projectID = (
                SELECT MAX(projectID) FROM IngestDB
            )
            GROUP BY ssid
            ORDER BY ssid_count DESC;
        """
        cursor.execute(query)
        wifi_data = cursor.fetchall()
        print(wifi_data)

        conn.close()

        # Map the fetched data into a list of dictionaries
        wifi_data_dict = [
            {"ssid": row[0], "count": row[1]}
            for row in wifi_data
        ]
        print("Fetched WiFi Data:", wifi_data_dict)
        return wifi_data_dict

    def get_wifiIn_data(self):
        return self.read_wifi_dataInternal()    

    def get_wifi_data(self):
        """Returns WiFi data to the frontend."""
        return self.read_wifi_data()

def main():
    # Run HeatmapApp on startup
    app = HeatmapApp()
    app.run()


if __name__ == '__main__':
    main()



