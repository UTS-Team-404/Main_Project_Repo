#!../.venv/bin/python3


import os
import folium
from folium.plugins import HeatMap
import csv
import webview



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
        m = folium.Map(location=[avg_lat, avg_lon], zoom_start=13)

        # Prepare data for the heatmap, adjusting signal strength for visibility
        norm_data = [[d[0], d[1], max(0, 100 + d[2])] for d in data]

        # Add heatmap to the map
        HeatMap(norm_data).add_to(m)

        # Save the map to the output file
        m.save(output_file)
        return output_file

class HeatmapApp:
    def __init__(self):
        self.generator = HeatmapGenerator()
        self.wifi_data = self.read_wifi_data()

    def read_wifi_data(self):
        """Reads WiFi data from the CSV file."""
        wifi_data = []
        try:
            with open('wifi_data.csv', 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    wifi_data.append({
                        'ssid': row['SSID'],
                        'signal_strength': row['Signal Strength'],
                        'channel': row['Channel'],
                        'encryption': row['Encryption']
                    })
        except FileNotFoundError:
            print("wifi_data.csv file not found.")
        except Exception as e:
            print(f"Error reading wifi_data.csv: {e}")
        return wifi_data

    def run(self):
        """Run the app and initialize the first heatmap."""
        # Create the initial heatmap
        self.generator.create_heatmap()

        # Start the PyWebView window
        html_path = os.path.join(os.path.dirname(__file__), 'index.html')
        webview.create_window('Heatmap Application', f"file://{html_path}", js_api=self)
        webview.start()

    def generate_new_heatmap(self):
        """Regenerate the heatmap."""
        self.generator.create_heatmap()
        print("Heatmap regenerated!")

    def get_wifi_data(self):
        """Returns WiFi data to the frontend."""
        return self.wifi_data

    def on_wifi_click(self, ssid):
        """Handle WiFi button click."""
        print(f"Connecting to {ssid}...")  # Here you could add more logic to connect to the WiFi


def main():
    # Run HeatmapApp on startup
    app = HeatmapApp()
    app.run()


if __name__ == '__main__':
    main()


