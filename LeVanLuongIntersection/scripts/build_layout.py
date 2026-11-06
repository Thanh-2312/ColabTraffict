"""Sinh hình học ngã tư Lê Văn Lương × Hoàng Đạo Thúy / Hoàng Minh Giám cho GAMA (advanced_driving).

Mọi số đo nằm trong ARMS / CORNER_R bên dưới. Đo thực địa xong thì sửa số ở đây rồi chạy lại:
    python scripts/build_layout.py
Đầu ra (UTM 48N / EPSG:32648, mét): includes/roads.geojson, includes/areas.geojson

Hệ tọa độ đo: mét, gốc O = tâm 4 nút OSM của ngã tư (21.005326 N, 105.804685 E), x = Đông, y = Bắc.
Mỗi nhánh: s = khoảng cách dọc trục nhánh tính từ O (hướng ra ngoài), t = lệch ngang, dương về phía TRÁI
khi nhìn ra ngoài (= phía chiều VÀO vì xe đi bên phải). Nguồn: ảnh Esri World Imagery 11/2025 (0,28 m/px);
riêng nhánh SE đo trên ảnh Esri Wayback 06/2023 rồi quy đổi về cùng khung (xem README).
"""
import json, math, os
from pyproj import Transformer
from shapely.geometry import LineString, Polygon, Point, mapping
from shapely.ops import unary_union

SUBLANE_W = 0.8   # m, bề rộng 1 sublane (1 xe máy, tính cả khe hở)
ARM_LEN = 150.0   # m, chiều dài mỗi nhánh đưa vào mô phỏng, tính từ O

ARMS = {  # bearing: phương vị trục nhánh (độ, từ Bắc theo chiều kim đồng hồ)
    #        c: tâm dải phân cách (t), med: rộng dải phân cách, w_in / w_out: rộng lòng đường chiều vào / ra (bó vỉa–bó vỉa)
    #        cw: vạch qua đường [mép trong, mép ngoài] (s), stop: vạch dừng chiều vào (s), nose: mũi dải phân cách (s)
    'NE': dict(name='Lê Văn Lương (hướng Láng Hạ)', bearing=53.4, c=-2.10, med=7.8, w_in=13.3, w_out=12.7, cw=(14.1, 17.7), stop=19.8, nose=17.4),
    'SE': dict(name='Hoàng Đạo Thúy (hướng Nhân Hòa)', bearing=128.5, c=-6.11, med=2.5, w_in=13.5, w_out=9.2, cw=(23.3, 26.5), stop=28.5, nose=28.3),
    'SW': dict(name='Lê Văn Lương (hướng Khuất Duy Tiến)', bearing=232.8, c=1.05, med=7.9, w_in=12.8, w_out=12.4, cw=(19.6, 22.9), stop=24.9, nose=21.8),
    'NW': dict(name='Hoàng Minh Giám (hướng Trung Hòa)', bearing=316.4, c=1.40, med=2.6, w_in=11.9, w_out=9.9, cw=(20.1, 23.4), stop=25.4, nose=23.7),
}
CLOCKWISE = ['NE', 'SE', 'SW', 'NW']
CORNER_R = {'E': 9.0, 'S': 9.0, 'W': 9.0, 'N': 9.0}  # bán kính bó vỉa góc, góc nằm giữa nhánh i và nhánh kế tiếp theo chiều kim đồng hồ
CORNER_OF = {('NE', 'SE'): 'E', ('SE', 'SW'): 'S', ('SW', 'NW'): 'W', ('NW', 'NE'): 'N'}

LAT0, LON0 = 21.005326, 105.804685
KX, KY = 111320 * math.cos(math.radians(LAT0)), 110574


def frame(a):
    b = math.radians(ARMS[a]['bearing'])
    return (math.sin(b), math.cos(b)), (-math.cos(b), math.sin(b))  # u (ra ngoài), v (bên trái u)


def P(a, s, t):
    (ux, uy), (vx, vy) = frame(a)
    return (s * ux + t * vx, s * uy + t * vy)


def edges(a):
    """t của 4 mép: ngoài chiều vào, trong chiều vào, trong chiều ra, ngoài chiều ra."""
    A = ARMS[a]
    return A['c'] + A['med'] / 2 + A['w_in'], A['c'] + A['med'] / 2, A['c'] - A['med'] / 2, A['c'] - A['med'] / 2 - A['w_out']


def n_sub(w):
    return int(math.floor(w / SUBLANE_W + 1e-9))


_TO_UTM = Transformer.from_crs('EPSG:4326', 'EPSG:32648', always_xy=True)


def ll(pt):
    # GAMA không tự chiếu GeoJSON lon/lat (thế giới sẽ tính bằng độ) → ghi thẳng UTM 48N, đơn vị mét
    x, y = _TO_UTM.transform(LON0 + pt[0] / KX, LAT0 + pt[1] / KY)
    return [round(x, 3), round(y, 3)]


def feature(geom, **props):
    g = mapping(geom)
    conv = lambda ring: [ll(p) for p in ring]
    if g['type'] == 'LineString':
        g = {'type': 'LineString', 'coordinates': conv(g['coordinates'])}
    elif g['type'] == 'Polygon':
        g = {'type': 'Polygon', 'coordinates': [conv(r) for r in g['coordinates']]}
    else:
        raise ValueError(g['type'])
    return {'type': 'Feature', 'geometry': g, 'properties': props}


def build():
    BIG = ARM_LEN * 3
    # --- khối vỉa hè 4 góc: phần nằm ngoài cả hai mép ngoài của 2 nhánh kề nhau, bo góc bán kính R
    blocks = []
    for i, a in enumerate(CLOCKWISE):
        b = CLOCKWISE[(i + 1) % 4]
        t_out_a = edges(a)[3]  # mép ngoài chiều ra của a (phía phải khi nhìn ra ngoài)
        t_in_b = edges(b)[0]   # mép ngoài chiều vào của b (phía trái khi nhìn ra ngoài)
        # nửa mặt phẳng t < t_out_a (trong khung a) ∩ nửa mặt phẳng t > t_in_b (trong khung b)
        ha = Polygon([P(a, -BIG, t_out_a), P(a, BIG, t_out_a), P(a, BIG, t_out_a - BIG), P(a, -BIG, t_out_a - BIG)])
        hb = Polygon([P(b, -BIG, t_in_b), P(b, BIG, t_in_b), P(b, BIG, t_in_b + BIG), P(b, -BIG, t_in_b + BIG)])
        R = CORNER_R[CORNER_OF[(a, b)]]
        blk = ha.intersection(hb).intersection(Point(0, 0).buffer(ARM_LEN + 30)).buffer(-R, join_style=1).buffer(R, join_style=1)
        blocks.append(blk)
    disk = Point(0, 0).buffer(ARM_LEN, resolution=64)
    paved = disk.difference(unary_union(blocks))

    medians = []
    for a, A in ARMS.items():
        _, ti, to, _ = edges(a)
        m = Polygon([P(a, A['nose'], ti), P(a, ARM_LEN + 5, ti), P(a, ARM_LEN + 5, to), P(a, A['nose'], to)])
        # mũi dải phân cách bo tròn theo nửa bề rộng (đúng kiểu mũi tròn trên ảnh vệ tinh)
        r = A['med'] / 2
        m = m.union(Point(P(a, A['nose'] + r, A['c'])).buffer(r)).difference(
            Polygon([P(a, A['nose'] - 50, ti + 1), P(a, A['nose'], ti + 1), P(a, A['nose'], to - 1), P(a, A['nose'] - 50, to - 1)]))
        medians.append(m.intersection(disk))
    road_surface = paved.difference(unary_union(medians))

    # --- vùng xung đột: mặt đường nằm phía trong vạch dừng (chiều vào) và mép ngoài vạch qua đường (chiều ra)
    cuts = []
    for a, A in ARMS.items():
        to_in, ti, to, to_out = edges(a)
        cuts.append(Polygon([P(a, A['stop'], ti - 0.01), P(a, BIG, ti - 0.01), P(a, BIG, to_in + BIG), P(a, A['stop'], to_in + BIG)]))
        cuts.append(Polygon([P(a, A['cw'][1], to_out - BIG), P(a, BIG, to_out - BIG), P(a, BIG, ti - 0.01), P(a, A['cw'][1], ti - 0.01)]))
    conflict = road_surface.difference(unary_union(cuts))
    if conflict.geom_type != 'Polygon':
        conflict = max(conflict.geoms, key=lambda g: g.area)

    areas, roads = [], []
    areas.append(feature(road_surface if road_surface.geom_type == 'Polygon' else max(road_surface.geoms, key=lambda g: g.area), kind='asphalt'))
    for m in medians:
        areas.append(feature(m if m.geom_type == 'Polygon' else max(m.geoms, key=lambda g: g.area), kind='median'))
    areas.append(feature(conflict, kind='conflict', area_m2=round(conflict.area, 1)))

    for a, A in ARMS.items():
        t_in_out, ti, to, t_out_out = edges(a)
        # vạch qua đường (cắt theo mặt đường để không chờm lên vỉa hè / dải phân cách)
        cw = Polygon([P(a, A['cw'][0], t_out_out - 1), P(a, A['cw'][1], t_out_out - 1), P(a, A['cw'][1], t_in_out + 1), P(a, A['cw'][0], t_in_out + 1)])
        cw = cw.intersection(paved)
        for g in (cw.geoms if hasattr(cw, 'geoms') else [cw]):
            if g.area > 1: areas.append(feature(g, kind='crosswalk', arm=a))
        areas.append(feature(LineString([P(a, A['stop'], ti), P(a, A['stop'], t_in_out)]), kind='stopline', arm=a))
        # đường chia sublane (chỉ để hiển thị)
        for side, t0, w, s0 in (('in', ti, A['w_in'], A['stop']), ('out', to, -A['w_out'], A['cw'][1])):
            n = n_sub(abs(w))
            for k in range(1, n):
                t = t0 + math.copysign(k * SUBLANE_W, w)
                areas.append(feature(LineString([P(a, s0, t), P(a, ARM_LEN, t)]), kind='sublane', arm=a, side=side))

        # --- road (đồ thị advanced_driving). Polyline nằm ở mép phía dải phân cách; GAMA vẽ xe lệch sang PHẢI, sublane 0 sát bó vỉa
        n_in, n_out = n_sub(A['w_in']), n_sub(A['w_out'])
        roads.append(feature(LineString([P(a, ARM_LEN, ti), P(a, A['stop'], ti)]), id=f'{a}_in', kind='approach', arm=a, to_arm='',
                             turn='', num_lanes=n_in, width=A['w_in'], name=A['name']))
        roads.append(feature(LineString([P(a, A['cw'][1], to), P(a, ARM_LEN, to)]), id=f'{a}_out', kind='exit', arm=a, to_arm='',
                             turn='', num_lanes=n_out, width=A['w_out'], name=A['name']))

    # --- đoạn nối trong vùng xung đột: mọi cặp vào → ra (trừ quay đầu), cong Bezier bậc 2 theo hướng 2 nhánh
    turn_of = {1: 'left', 2: 'through', 3: 'right'}  # số bước theo chiều kim đồng hồ từ nhánh vào tới nhánh ra
    for i, a in enumerate(CLOCKWISE):
        for j, b in enumerate(CLOCKWISE):
            k = (j - i) % 4
            if k == 0: continue
            turn = turn_of[k]  # xe đi bên phải: rẽ phải = nhánh kế bên ngược chiều kim đồng hồ (k = 3)
            A, B = ARMS[a], ARMS[b]
            p0, p1 = P(a, A['stop'], edges(a)[1]), P(b, B['cw'][1], edges(b)[2])
            (ua, _), (ub, _) = frame(a), frame(b)
            d0 = (-ua[0], -ua[1])  # hướng đi vào tâm
            # điểm điều khiển: giao của 2 tia (vào theo d0, ra ngược ub); nếu gần song song (đi thẳng) lấy trung điểm
            den = d0[0] * (-ub[1]) - d0[1] * (-ub[0])
            if abs(den) < 0.2:
                c = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            else:
                lam = ((p1[0] - p0[0]) * (-ub[1]) - (p1[1] - p0[1]) * (-ub[0])) / den
                c = (p0[0] + lam * d0[0], p0[1] + lam * d0[1])
            pts = [((1 - q) ** 2 * p0[0] + 2 * (1 - q) * q * c[0] + q * q * p1[0], (1 - q) ** 2 * p0[1] + 2 * (1 - q) * q * c[1] + q * q * p1[1])
                   for q in (x / 12 for x in range(13))]
            n = min(n_sub(A['w_in']), n_sub(B['w_out']))
            roads.append(feature(LineString(pts), id=f'{a}_{b}', kind='connector', arm=a, to_arm=b, turn=turn, num_lanes=n,
                                 width=round(n * SUBLANE_W, 2), name=''))
    return roads, areas, conflict, paved


def angles():
    out = []
    for i, a in enumerate(CLOCKWISE):
        b = CLOCKWISE[(i + 1) % 4]
        out.append((a, b, (ARMS[b]['bearing'] - ARMS[a]['bearing']) % 360))
    return out


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')  # console Windows mặc định cp1252
    here =os.path.dirname(os.path.abspath(__file__))
    inc = os.path.join(here, '..', 'includes')
    os.makedirs(inc, exist_ok=True)
    roads, areas, conflict, _ = build()
    for fn, feats in (('roads.geojson', roads), ('areas.geojson', areas)):
        # GAMA lấy schema từ feature đầu tiên → mọi feature phải có cùng bộ thuộc tính, cùng kiểu
        keys = {}
        for f in feats:
            for k, v in f['properties'].items():
                keys.setdefault(k, 0.0 if isinstance(v, (int, float)) else '')
        for f in feats:
            f['properties'] = {k: f['properties'].get(k, d) for k, d in keys.items()}
        with open(os.path.join(inc, fn), 'w', encoding='utf-8') as f:
            json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:32648'}},
                       'features': feats}, f, ensure_ascii=False)
    # self-check: tổng góc = 360, sublane đúng công thức, vùng xung đột là 1 đa giác hợp lệ
    assert abs(sum(x[2] for x in angles()) - 360) < 1e-6
    assert all(r['properties']['num_lanes'] == n_sub(r['properties']['width']) for r in roads)
    assert conflict.is_valid and conflict.area > 500
    print(f'{"nhánh":4} {"chiều":5} {"rộng(m)":>8} {"sublane":>8} {"dư(m)":>6}')
    for a, A in ARMS.items():
        for side in ('in', 'out'):
            w = A['w_' + side]
            print(f'{a:4} {side:5} {w:8.1f} {n_sub(w):8d} {w - n_sub(w) * SUBLANE_W:6.2f}')
    print('góc giữa các nhánh kề nhau:', ', '.join(f'{a}-{b} {g:.1f}°' for a, b, g in angles()))
    print(f'vùng xung đột: {conflict.area:.0f} m²; roads: {len(roads)}; areas: {len(areas)}')
