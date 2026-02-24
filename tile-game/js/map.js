/**
 * Benicia Tile Matcher - Map Interaction (Leaflet + OpenStreetMap)
 * Handles real map rendering, marker zones, clicks, highlights, and animations
 */

const MapController = (function () {
  let leafletMap = null;
  let onZoneClick = null;
  let matchedZones = new Set();
  let disabledZones = new Set();
  let markers = new Map(); // zoneId -> L.marker

  // Zone positions for the Leaflet map
  // Organized by block and side for layout (kept for highlightHint and getZoneLayout)
  const ZONE_LAYOUT = {
    east: [
      { id: "zone-15", block: 600, label: "15" },
      { id: "zone-14", block: 700, label: "14" },
      { id: "zone-13", block: 700, label: "13" },
      { id: "zone-12", block: 700, label: "12" },
      { id: "zone-22", block: 800, label: "22" },
      { id: "zone-11", block: 800, label: "11" },
      { id: "zone-10", block: 800, label: "10" },
      { id: "zone-9", block: 800, label: "9" },
      { id: "zone-8", block: 900, label: "8" },
      { id: "zone-7", block: 900, label: "7" },
      { id: "zone-6", block: 900, label: "6" },
      { id: "zone-5", block: 1000, label: "5" },
      { id: "zone-1", block: 1150, label: "1" },
      { id: "zone-2", block: 1150, label: "2" },
      { id: "zone-3", block: 1150, label: "3" },
      { id: "zone-4", block: 1150, label: "4" },
    ],
    west: [
      { id: "zone-16", block: 600, label: "16" },
      { id: "zone-17", block: 650, label: "17" },
      { id: "zone-18", block: 700, label: "18" },
      { id: "zone-19", block: 700, label: "19" },
      { id: "zone-20", block: 700, label: "20" },
      { id: "zone-21", block: 800, label: "21" },
      { id: "zone-23", block: 800, label: "23" },
      { id: "zone-24", block: 900, label: "24" },
      { id: "zone-25", block: 900, label: "25" },
      { id: "zone-26", block: 900, label: "26" },
      { id: "zone-27", block: 1000, label: "27" },
      { id: "zone-28", block: 1000, label: "28" },
    ],
  };

  // Real-world lat/lng coordinates for each zone
  // Source: Google My Maps "First Street Tile Walk"
  // https://www.google.com/maps/d/viewer?mid=1PaaXn133YJ3dTcIHRCION2HPqpvpCoM
  const ZONE_COORDS = {
    // === East side (waterfront side of street) ===
    "zone-1":  { lat: 38.0533771, lng: -122.1558933 }, // World War I
    "zone-2":  { lat: 38.0533074, lng: -122.1559403 }, // World War II
    "zone-3":  { lat: 38.0532324, lng: -122.1559926 }, // Korean War
    "zone-4":  { lat: 38.0531553, lng: -122.1560529 }, // Vietnam War
    "zone-5":  { lat: 38.0522081, lng: -122.1567042 }, // Benicia Boy
    "zone-6":  { lat: 38.0520676, lng: -122.1567981 }, // St. Paul's
    "zone-7":  { lat: 38.0516846, lng: -122.1570953 }, // Concepcion
    "zone-8":  { lat: 38.0513906, lng: -122.1573205 }, // Collegiate Institute
    "zone-9":  { lat: 38.0512587, lng: -122.1574172 }, // Young Ladies Seminary
    "zone-10": { lat: 38.0509159, lng: -122.1576812 }, // Great Barge Fight
    "zone-11": { lat: 38.0505989, lng: -122.1579050 }, // Guard House
    "zone-12": { lat: 38.0504792, lng: -122.1580020 }, // Pacific Mail
    "zone-13": { lat: 38.0500738, lng: -122.1582879 }, // Congregational Church
    "zone-14": { lat: 38.0497913, lng: -122.1584940 }, // Jack London
    "zone-15": { lat: 38.0496574, lng: -122.1586004 }, // St. Dominic's
    "zone-22": { lat: 38.0510486, lng: -122.1577551 }, // Dona Vallejo

    // === West side (inland side of street) ===
    "zone-16": { lat: 38.0497433, lng: -122.1587197 }, // Semple & Larkin
    "zone-17": { lat: 38.0499268, lng: -122.1588351 }, // Granizo's Art
    "zone-18": { lat: 38.0498392, lng: -122.1586435 }, // State Capitol
    "zone-19": { lat: 38.0501216, lng: -122.1584446 }, // Firefighters
    "zone-20": { lat: 38.0505411, lng: -122.1581335 }, // Bella Union
    "zone-21": { lat: 38.0506609, lng: -122.1580442 }, // The Solano
    "zone-23": { lat: 38.0513485, lng: -122.1575466 }, // Captain Walsh
    "zone-24": { lat: 38.0514544, lng: -122.1574715 }, // Cherish Our Past
    "zone-25": { lat: 38.0517570, lng: -122.1572271 }, // Benicia Barracks
    "zone-26": { lat: 38.0521195, lng: -122.1569838 }, // Masonic Temple
    "zone-27": { lat: 38.0523069, lng: -122.1568496 }, // Commandant's Home
    "zone-28": { lat: 38.0525969, lng: -122.1566397 }, // Clock Tower
  };

  // Build a quick lookup: zoneId -> { label, block, side }
  const zoneLookup = {};
  Object.entries(ZONE_LAYOUT).forEach(([side, zones]) => {
    zones.forEach((z) => {
      zoneLookup[z.id] = { label: z.label, block: z.block, side: side };
    });
  });

  function createMarkerIcon(label, extraClass) {
    return L.divIcon({
      className: "leaflet-zone-marker " + (extraClass || ""),
      html:
        '<div class="map-zone" data-zone-id="zone-' + label + '">' +
          '<div class="zone-circle">' +
            '<span class="zone-label">' + label + "</span>" +
          "</div>" +
        "</div>",
      iconSize: [40, 40],
      iconAnchor: [20, 20],
    });
  }

  function initMap(containerId) {
    const container = document.getElementById(containerId);

    leafletMap = L.map(container, {
      center: [38.0514, -122.1577],
      zoom: 17,
      minZoom: 15,
      maxZoom: 19,
      zoomControl: true,
      attributionControl: true,
      scrollWheelZoom: false, // Prevent scroll hijacking on mobile
      tap: true,
      tapTolerance: 15,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19,
    }).addTo(leafletMap);
  }

  function addMarkers() {
    const allCoords = [];

    Object.entries(ZONE_COORDS).forEach(([zoneId, coord]) => {
      const zoneData = zoneLookup[zoneId];
      if (!zoneData) return;

      const icon = createMarkerIcon(zoneData.label);
      const marker = L.marker([coord.lat, coord.lng], {
        icon: icon,
        interactive: true,
        keyboard: true,
        zIndexOffset: zoneData.side === "east" ? 100 : 0, // East side on top
      }).addTo(leafletMap);

      marker.on("click", function () {
        if (matchedZones.has(zoneId) || disabledZones.has(zoneId)) {
          return;
        }
        if (onZoneClick) {
          onZoneClick(zoneId);
        }
      });

      markers.set(zoneId, marker);
      allCoords.push([coord.lat, coord.lng]);
    });

    // Fit bounds to show all markers with padding
    if (allCoords.length > 0) {
      leafletMap.fitBounds(allCoords, { padding: [30, 30] });
    }
  }

  return {
    init(containerId, clickCallback) {
      onZoneClick = clickCallback;
      initMap(containerId);
      addMarkers();
    },

    flashCorrect(zoneId) {
      const marker = markers.get(zoneId);
      if (!marker) return;

      matchedZones.add(zoneId);
      const zoneData = zoneLookup[zoneId];
      if (zoneData) {
        marker.setIcon(createMarkerIcon(zoneData.label, "zone-correct"));
      }
    },

    flashIncorrect(zoneId) {
      const marker = markers.get(zoneId);
      if (!marker) return;

      const el = marker.getElement();
      if (el) {
        const zone = el.querySelector(".map-zone");
        if (zone) {
          zone.classList.add("zone-incorrect");
          setTimeout(() => zone.classList.remove("zone-incorrect"), 600);
        }
      }
    },

    highlightHint(currentTile, clickedZoneId) {
      const clicked = zoneLookup[clickedZoneId];
      if (!clicked) return "";

      const targetBlock = currentTile.block;
      const targetSide = currentTile.side;

      let hint = "";
      if (clicked.side !== targetSide) {
        hint = "Try the " + targetSide + " side of the street.";
      } else if (clicked.block < targetBlock) {
        hint = "Try further east along First Street.";
      } else if (clicked.block > targetBlock) {
        hint = "Try further west along First Street.";
      } else {
        hint = "You're in the right block! Try a different spot.";
      }
      return hint;
    },

    resetMap() {
      matchedZones.clear();
      disabledZones.clear();

      markers.forEach((marker, zoneId) => {
        const zoneData = zoneLookup[zoneId];
        if (zoneData) {
          marker.setIcon(createMarkerIcon(zoneData.label));
        }
      });
    },

    refresh() {
      if (leafletMap) {
        setTimeout(function () {
          leafletMap.invalidateSize();
          // Re-fit bounds after resize
          const allCoords = Object.values(ZONE_COORDS).map(function (c) {
            return [c.lat, c.lng];
          });
          if (allCoords.length > 0) {
            leafletMap.fitBounds(allCoords, { padding: [30, 30] });
          }
        }, 100);
      }
    },

    getZoneLayout() {
      return ZONE_LAYOUT;
    },
  };
})();
