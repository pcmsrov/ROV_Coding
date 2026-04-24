/**
 * @file smart_pill_box.scad
 * @description 智慧藥盒（參考圖）參數化模型
 * @author ChatGPT
 * @version 1.0.0
 *
 * 使用方式：
 * 1) 直接 F5 預覽
 * 2) 若要輸出列印，切換 assembly_mode
 *    - "assembled": 組裝預覽（蓋子打開）
 *    - "base_only": 只顯示底座
 *    - "lid_only": 只顯示上蓋
 */

/** ===================== 參數區 ===================== **/
$fn = 64;

/** 組裝模式： "assembled" / "base_only" / "lid_only" */
assembly_mode = "assembled";

/** 主要尺寸（mm） */
box_len = 225;          // 總長
box_wid = 95;           // 總寬
box_hgt = 30;           // 底座高度（不含上蓋）
corner_r = 14;          // 外圓角
wall = 2.4;             // 外殼壁厚
bottom_thk = 2.2;       // 底板厚度

/** 內部 7 天格子區 */
days_count = 7;
display_zone_len = 45;  // 右側螢幕/電路區長度
inner_margin = 4;       // 內部邊距
divider_thk = 1.8;      // 分隔板厚
compartment_depth = 23; // 格子深度（從底部算）

/** 上蓋 */
lid_thk = 2.2;
lid_clearance = 0.4;    // 蓋與底的間隙
lid_frame_drop = 7;     // 蓋內框下垂（壓住底座）
lid_open_angle = 225;   // 蓋子打開角度（組裝模式使用）

/** 鉸鏈（簡化） */
hinge_bar_r = 1.8;
hinge_knuckle_len = 12;
hinge_gap = 0.35;

/** 右側螢幕 */
screen_w = 27;
screen_h = 20;
screen_corner = 2.5;
screen_depth = 1.2;

/** ===================== 工具函式 ===================== **/

/**
 * @function rounded_box
 * @description 建立圓角長方體（2D 圓角拉伸）
 * @param {number} x 長度
 * @param {number} y 寬度
 * @param {number} z 高度
 * @param {number} r 圓角半徑
 */
module rounded_box(x, y, z, r) {
    linear_extrude(height = z)
        offset(r = r)
            offset(delta = -r)
                square([x, y], center = false);
}

/**
 * @function rounded_rect_2d
 * @description 建立 2D 圓角矩形
 * @param {number} x 長度
 * @param {number} y 寬度
 * @param {number} r 圓角
 */
module rounded_rect_2d(x, y, r) {
    offset(r = r)
        offset(delta = -r)
            square([x, y], center = false);
}

/** ===================== 主零件 ===================== **/

/**
 * @function base_shell
 * @description 底座外殼 + 內腔 + 7 格分隔 + 右側螢幕凹槽
 */
module base_shell() {
    difference() {
        // 外殼
        color([1.0, 0.78, 0.84])
            rounded_box(box_len, box_wid, box_hgt, corner_r);

        // 內腔挖空
        translate([wall, wall, bottom_thk])
            rounded_box(
                box_len - 2*wall,
                box_wid - 2*wall,
                box_hgt - bottom_thk + 0.1,
                max(corner_r - wall, 2)
            );

        // 藥格區上方開口（只保留分隔板）
        comp_zone_len = box_len - display_zone_len - inner_margin*2;
        comp_zone_wid = box_wid - inner_margin*2;

        // 先挖整塊區域（留分隔板後面再補）
        translate([inner_margin, inner_margin, bottom_thk + 0.8])
            cube([comp_zone_len, comp_zone_wid, compartment_depth], center = false);

        // 右側螢幕凹槽
        translate([
            box_len - display_zone_len + (display_zone_len - screen_w)/2,
            (box_wid - screen_h)/2,
            box_hgt - screen_depth
        ])
            linear_extrude(height = screen_depth + 0.2)
                rounded_rect_2d(screen_w, screen_h, screen_corner);
    }

    // 7 天分隔板（沿長度分）
    comp_zone_len = box_len - display_zone_len - inner_margin*2;
    comp_zone_wid = box_wid - inner_margin*2;
    cell_len = (comp_zone_len - divider_thk*(days_count - 1)) / days_count;

    for (i = [1 : days_count-1]) {
        x_pos = inner_margin + i*cell_len + (i-1)*divider_thk;
        color([1.0, 0.75, 0.82])
            translate([x_pos, inner_margin, bottom_thk])
                cube([divider_thk, comp_zone_wid, compartment_depth], center = false);
    }

    // 分隔區與顯示區之間擋板
    x_sep = inner_margin + comp_zone_len;
    color([1.0, 0.75, 0.82])
        translate([x_sep, inner_margin, bottom_thk])
            cube([divider_thk, comp_zone_wid, compartment_depth], center = false);

    // 右側顯示區面板（略微凸起）
    color([1.0, 0.80, 0.86])
        translate([box_len - display_zone_len + 3, 8, box_hgt - 1.2])
            rounded_box(display_zone_len - 6, box_wid - 16, 1.2, 4);
}

/**
 * @function lid_shell
 * @description 上蓋（透明粉色風格，含內框）
 */
module lid_shell() {
    lid_x = box_len;
    lid_y = box_wid;
    lid_z = 8.5;

    color([1.0, 0.82, 0.88, 0.45])  // 含透明度
    difference() {
        rounded_box(lid_x, lid_y, lid_z, corner_r);

        // 蓋子內部掏空
        translate([lid_thk, lid_thk, lid_thk])
            rounded_box(
                lid_x - 2*lid_thk,
                lid_y - 2*lid_thk,
                lid_z - lid_thk + 0.1,
                max(corner_r - lid_thk, 2)
            );
    }

    // 蓋內框（向下伸，套住底座）
    color([1.0, 0.82, 0.88, 0.45])
    difference() {
        translate([wall + lid_clearance, wall + lid_clearance, -lid_frame_drop])
            rounded_box(
                box_len - 2*(wall + lid_clearance),
                box_wid - 2*(wall + lid_clearance),
                lid_frame_drop,
                max(corner_r - (wall + lid_clearance), 2)
            );

        translate([wall + lid_clearance + 1.2, wall + lid_clearance + 1.2, -lid_frame_drop - 0.1])
            rounded_box(
                box_len - 2*(wall + lid_clearance + 1.2),
                box_wid - 2*(wall + lid_clearance + 1.2),
                lid_frame_drop + 0.2,
                max(corner_r - (wall + lid_clearance + 1.2), 1)
            );
    }
}

/**
 * @function hinge_pair
 * @description 簡化鉸鏈（底座端 + 蓋子端）
 */
module hinge_pair() {
    hinge_y = box_wid/2 - hinge_knuckle_len*1.5;
    x0 = box_len - 10;

    // 底座端 knuckles
    for (j = [0:2]) {
        if (j % 2 == 0) {
            translate([x0, hinge_y + j*hinge_knuckle_len, box_hgt - 4])
                rotate([0,90,0])
                    cylinder(h = 8, r = hinge_bar_r, center = false);
        }
    }

    // 蓋子端 knuckle（中間）
    translate([x0 + hinge_gap, hinge_y + hinge_knuckle_len, box_hgt + 1])
        rotate([0,90,0])
            cylinder(h = 8, r = hinge_bar_r, center = false);

    // 鉸鏈軸
    translate([x0 + 1.5, hinge_y - 0.5, box_hgt - 1.5])
        rotate([0,90,0])
            cylinder(h = 5.5, r = 0.9, center = false);
}

/** ===================== 組裝 ===================== **/

module assembled() {
    // 底座
    base_shell();

    // 鉸鏈
    color([0.92, 0.68, 0.76]) hinge_pair();

    // 蓋子（繞後緣旋轉打開）
    // 以左後角附近作為旋轉樞軸，視覺上接近圖片
    translate([0, box_wid, box_hgt - 1.2])
        rotate([lid_open_angle, 0, 0])
            translate([0, -box_wid, 0])
                lid_shell();
    compartment_lids(); // 7 個藥格小蓋子
}

if (assembly_mode == "assembled") {
    assembled();
} else if (assembly_mode == "base_only") {
    base_shell();
} else if (assembly_mode == "lid_only") {
    lid_shell();
} else {
    assembled();
}
/**
 * @description 小蓋子參數
 */
lid_gap = 0.6;              // 小蓋子與格子邊界間隙
small_lid_thk = 1.6;        // 小蓋子厚度
small_lid_open_angle_default = 15; // 預設小蓋開啟角度（度）
small_lid_open_angles = [15, 15, 15, 15, 15, 15, 15]; // 每格獨立角度（對應 7 格）
small_hinge_r = 0.9;        // 小蓋鉸鏈半徑

/**
 * @function one_compartment_lid
 * @description 建立單一藥格的小翻蓋（含簡化鉸鏈）
 * @param {number} x 藥格起始 x
 * @param {number} y 藥格起始 y
 * @param {number} w 藥格寬度（沿 x）
 * @param {number} d 藥格深度（沿 y）
 * @param {number} z_top 蓋子所在 z 高度
 * @param {number} open_angle 該格小蓋開啟角度
 */
module one_compartment_lid(x, y, w, d, z_top, open_angle) {
    lid_w = w - 2*lid_gap;
    lid_d = d - 2*lid_gap;

    // 以後側邊作為旋轉軸（沿 x 方向）
    hinge_x = x + lid_gap;
    hinge_y = y + d - 0.8;  // 靠近藥格後緣
    hinge_z = z_top + 0.2;

    // 小蓋主體（可旋轉）
    color([1.0, 0.82, 0.88, 0.40])
    translate([hinge_x, hinge_y, hinge_z])
        rotate([open_angle, 0, 0])
            translate([0, -lid_d, 0])
                linear_extrude(height = small_lid_thk)
                    offset(r = 1.2)
                        offset(delta = -1.2)
                            square([lid_w, lid_d], center = false);

    // 簡化鉸鏈（固定在後側）
    color([0.95, 0.70, 0.80])
    translate([hinge_x, hinge_y, z_top])
        rotate([0, 90, 0])
            cylinder(h = lid_w, r = small_hinge_r, center = false);
}

/**
 * @function compartment_lids
 * @description 為 7 個藥格建立各自小蓋子
 */
module compartment_lids() {
    comp_zone_len = box_len - display_zone_len - inner_margin*2;
    comp_zone_wid = box_wid - inner_margin*2;
    cell_len = (comp_zone_len - divider_thk*(days_count - 1)) / days_count;

    // 小蓋子放在藥格頂部附近
    z_top = bottom_thk + compartment_depth + 0.3;

    for (i = [0 : days_count-1]) {
        x0 = inner_margin + i*(cell_len + divider_thk);
        y0 = inner_margin;
        open_angle = (i < len(small_lid_open_angles))
            ? small_lid_open_angles[i]
            : small_lid_open_angle_default;
        one_compartment_lid(x0, y0, cell_len, comp_zone_wid, z_top, open_angle);
    }
}