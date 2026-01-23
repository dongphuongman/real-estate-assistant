import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import PropertyMap from "../property-map";

const fitBoundsMock = jest.fn();
const divIconMock = jest.fn(() => ({}));

jest.mock("leaflet", () => ({
  divIcon: (...args: unknown[]) => divIconMock(...args),
}));

jest.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div data-testid="map">{children}</div>,
  TileLayer: () => <div data-testid="tile" />,
  Marker: ({ children, position }: { children: ReactNode; position: unknown }) => (
    <div data-testid="marker" data-position={JSON.stringify(position)}>
      {children}
    </div>
  ),
  Popup: ({ children }: { children: ReactNode }) => <div data-testid="popup">{children}</div>,
  useMap: () => ({ fitBounds: fitBoundsMock }),
  useMapEvents: () => ({ getZoom: () => 12 }),
}));

describe("PropertyMap", () => {
  beforeEach(() => {
    fitBoundsMock.mockClear();
    divIconMock.mockClear();
  });

  it("renders markers and popup content for points", () => {
    render(
      <PropertyMap
        points={[
          { id: "a", lat: 52.23, lon: 21.01, title: "A", city: "Warsaw", country: "PL", price: 100000 },
          { id: "b", lat: 52.24, lon: 21.02, title: "B", city: "Warsaw", country: "PL" },
        ]}
      />
    );

    expect(screen.getAllByTestId("marker")).toHaveLength(2);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getAllByText("Warsaw, PL")).toHaveLength(2);
    expect(screen.getByText("$100,000")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
  });

  it("fits bounds when points are present", () => {
    render(<PropertyMap points={[{ id: "a", lat: 1, lon: 2 }, { id: "b", lat: 3, lon: 4 }]} />);
    expect(fitBoundsMock).toHaveBeenCalledTimes(1);
    expect(fitBoundsMock).toHaveBeenCalledWith(
      [
        [1, 2],
        [3, 4],
      ],
      { padding: [24, 24] }
    );
  });

  it("does not fit bounds when no points are present", () => {
    render(<PropertyMap points={[]} />);
    expect(fitBoundsMock).not.toHaveBeenCalled();
  });

  it("clusters dense points and renders a cluster popup summary", () => {
    const points = Array.from({ length: 80 }, (_, idx) => ({
      id: `p-${idx}`,
      lat: 52.23 + idx * 0.000001,
      lon: 21.01 + idx * 0.000001,
      title: `Property ${idx}`,
      city: "Warsaw",
      country: "PL",
    }));

    render(<PropertyMap points={points} />);

    expect(screen.getAllByTestId("marker").length).toBeLessThan(points.length);
    expect(screen.getByText("80 properties in this area")).toBeInTheDocument();
    expect(screen.getByText("Property 0")).toBeInTheDocument();
  });
});
