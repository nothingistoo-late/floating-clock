using System;
using System.Drawing;
using System.IO;
using System.Windows.Forms;
using Microsoft.Win32;

namespace TopFloatingClock
{
    public class Config
    {
        public int X = -1;
        public int Y = 10;
        public double Opacity = 0.88;
        public float FontSize = 18f;
        public string TextColor = "#00FFCC";
        public string BgColor = "#11141a";
        public string BorderColor = "#2d3748";
        public bool Locked = false;
    }

    public class FloatingClockForm : Form
    {
        private Config config;
        private string configPath;
        private Timer timer;
        private Label lblTime;
        private Panel containerPanel;
        private ContextMenuStrip contextMenu;
        private bool isDragging = false;
        private Point dragCursorPoint;
        private Point dragFormPoint;

        public FloatingClockForm()
        {
            configPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "clock_config.json");
            LoadConfig();

            // Cấu hình Form không viền, always on top
            this.FormBorderStyle = FormBorderStyle.None;
            this.TopMost = true;
            this.ShowInTaskbar = false;
            this.StartPosition = FormStartPosition.Manual;
            this.BackColor = ColorTranslator.FromHtml(config.BorderColor);
            this.Opacity = config.Opacity;
            this.DoubleBuffered = true;
            this.Padding = new Padding(1); // 1px border ngoài
            this.AutoSize = true;
            this.AutoSizeMode = AutoSizeMode.GrowAndShrink;

            // Panel nền bên trong
            containerPanel = new Panel();
            containerPanel.BackColor = ColorTranslator.FromHtml(config.BgColor);
            containerPanel.Padding = new Padding(14, 4, 14, 4);
            containerPanel.Margin = new Padding(0);
            containerPanel.AutoSize = true;
            containerPanel.AutoSizeMode = AutoSizeMode.GrowAndShrink;
            this.Controls.Add(containerPanel);

            // Label hiển thị Giờ : Phút : Giây (HH:mm:ss)
            lblTime = new Label();
            lblTime.AutoSize = true;
            lblTime.Text = DateTime.Now.ToString("HH:mm:ss");
            lblTime.Font = new Font("Consolas", config.FontSize, FontStyle.Bold);
            lblTime.ForeColor = ColorTranslator.FromHtml(config.TextColor);
            lblTime.BackColor = Color.Transparent;
            lblTime.Margin = new Padding(0);
            lblTime.Padding = new Padding(0);
            containerPanel.Controls.Add(lblTime);

            // Menu chuột phải
            BuildContextMenu();

            // Bind sự kiện kéo thả chuột
            BindMouseEvents(this);
            BindMouseEvents(containerPanel);
            BindMouseEvents(lblTime);

            // Timer cập nhật đồng hồ
            timer = new Timer();
            timer.Interval = 100;
            timer.Tick += (s, e) =>
            {
                string now = DateTime.Now.ToString("HH:mm:ss");
                if (lblTime.Text != now)
                {
                    lblTime.Text = now;
                }
            };
            timer.Start();

            this.Load += (s, e) =>
            {
                PositionWindow();
            };
        }

        private void BindMouseEvents(Control ctrl)
        {
            ctrl.MouseDown += (s, e) =>
            {
                if (e.Button == MouseButtons.Left && !config.Locked)
                {
                    isDragging = true;
                    dragCursorPoint = Cursor.Position;
                    dragFormPoint = this.Location;
                }
                else if (e.Button == MouseButtons.Right)
                {
                    BuildContextMenu();
                    contextMenu.Show(Cursor.Position);
                }
            };

            ctrl.MouseMove += (s, e) =>
            {
                if (isDragging && !config.Locked)
                {
                    Point diff = Point.Subtract(Cursor.Position, new Size(dragCursorPoint));
                    this.Location = Point.Add(dragFormPoint, new Size(diff));
                }
            };

            ctrl.MouseUp += (s, e) =>
            {
                if (isDragging)
                {
                    isDragging = false;
                    config.X = this.Location.X;
                    config.Y = this.Location.Y;
                    SaveConfig();
                }
            };
        }

        private void PositionWindow()
        {
            Screen screen = Screen.PrimaryScreen;
            int x = config.X;
            int y = config.Y;

            if (x < 0)
            {
                x = (screen.WorkingArea.Width - this.Width) / 2;
                y = 10;
            }

            this.Location = new Point(x, y);
        }

        private void BuildContextMenu()
        {
            contextMenu = new ContextMenuStrip();
            contextMenu.RenderMode = ToolStripRenderMode.System;

            // Màu chữ
            ToolStripMenuItem colorMenu = new ToolStripMenuItem("🎨 Đổi màu chữ");
            string[,] colors = {
                { "Cyan Neon (Xanh ngọc)", "#00FFCC" },
                { "Lime Green (Xanh lá)", "#10B981" },
                { "Amber Gold (Vàng cam)", "#F59E0B" },
                { "Pink Neon (Hồng tím)", "#EC4899" },
                { "Sky Blue (Xanh dương)", "#38BDF8" },
                { "Pure White (Trắng)", "#FFFFFF" },
                { "Fire Red (Đỏ)", "#EF4444" }
            };

            for (int i = 0; i < colors.GetLength(0); i++)
            {
                string name = colors[i, 0];
                string hex = colors[i, 1];
                var item = new ToolStripMenuItem(name, null, (s, e) => SetTextColor(hex));
                colorMenu.DropDownItems.Add(item);
            }
            colorMenu.DropDownItems.Add(new ToolStripSeparator());
            colorMenu.DropDownItems.Add(new ToolStripMenuItem("Màu tùy chọn...", null, (s, e) => PickCustomColor()));
            contextMenu.Items.Add(colorMenu);

            // Độ trong suốt
            ToolStripMenuItem opacityMenu = new ToolStripMenuItem("🌫️ Độ trong suốt (Opacity)");
            double[] opacities = new double[] { 1.0, 0.88, 0.75, 0.6, 0.4 };
            foreach (double op in opacities)
            {
                double currentOp = op;
                var item = new ToolStripMenuItem(string.Format("{0}%", (int)(currentOp * 100)), null, (s, e) => SetOpacity(currentOp));
                if (Math.Abs(config.Opacity - currentOp) < 0.01) item.Checked = true;
                opacityMenu.DropDownItems.Add(item);
            }
            contextMenu.Items.Add(opacityMenu);

            // Cỡ chữ
            ToolStripMenuItem sizeMenu = new ToolStripMenuItem("🔤 Kích thước chữ");
            float[] sizes = new float[] { 14f, 16f, 18f, 20f, 24f, 28f, 32f };
            foreach (float sz in sizes)
            {
                float currentSize = sz;
                var item = new ToolStripMenuItem(string.Format("Cỡ {0}px", (int)currentSize), null, (s, e) => SetFontSize(currentSize));
                if (Math.Abs(config.FontSize - currentSize) < 0.1) item.Checked = true;
                sizeMenu.DropDownItems.Add(item);
            }
            contextMenu.Items.Add(sizeMenu);

            // Căn vị trí nhanh
            ToolStripMenuItem posMenu = new ToolStripMenuItem("📍 Căn vị trí nhanh");
            posMenu.DropDownItems.Add(new ToolStripMenuItem("Đỉnh giữa (Top Center)", null, (s, e) => AlignPosition(0)));
            posMenu.DropDownItems.Add(new ToolStripMenuItem("Đỉnh phải (Top Right)", null, (s, e) => AlignPosition(1)));
            posMenu.DropDownItems.Add(new ToolStripMenuItem("Đỉnh trái (Top Left)", null, (s, e) => AlignPosition(2)));
            posMenu.DropDownItems.Add(new ToolStripMenuItem("Đáy giữa (Bottom Center)", null, (s, e) => AlignPosition(3)));
            contextMenu.Items.Add(posMenu);

            contextMenu.Items.Add(new ToolStripSeparator());

            // Khóa vị trí
            var lockItem = new ToolStripMenuItem("🔒 Khóa vị trí", null, (s, e) => ToggleLock());
            lockItem.Checked = config.Locked;
            contextMenu.Items.Add(lockItem);

            // Khởi động cùng Windows
            var startupItem = new ToolStripMenuItem("🚀 Khởi động cùng Windows", null, (s, e) => ToggleStartup());
            startupItem.Checked = IsStartupEnabled();
            contextMenu.Items.Add(startupItem);

            contextMenu.Items.Add(new ToolStripSeparator());
            contextMenu.Items.Add(new ToolStripMenuItem("❌ Đóng đồng hồ", null, (s, e) => { SaveConfig(); Application.Exit(); }));
        }

        private void SetTextColor(string hex)
        {
            config.TextColor = hex;
            lblTime.ForeColor = ColorTranslator.FromHtml(hex);
            SaveConfig();
        }

        private void PickCustomColor()
        {
            using (ColorDialog dlg = new ColorDialog())
            {
                dlg.Color = lblTime.ForeColor;
                if (dlg.ShowDialog() == DialogResult.OK)
                {
                    string hex = "#" + dlg.Color.R.ToString("X2") + dlg.Color.G.ToString("X2") + dlg.Color.B.ToString("X2");
                    SetTextColor(hex);
                }
            }
        }

        private void SetOpacity(double val)
        {
            config.Opacity = val;
            this.Opacity = val;
            SaveConfig();
        }

        private void SetFontSize(float sz)
        {
            config.FontSize = sz;
            lblTime.Font = new Font("Consolas", sz, FontStyle.Bold);
            this.Refresh();
            SaveConfig();
        }

        private void AlignPosition(int mode)
        {
            Screen screen = Screen.PrimaryScreen;
            int x = 0, y = 10;
            switch (mode)
            {
                case 0:
                    x = (screen.WorkingArea.Width - this.Width) / 2;
                    y = 10;
                    break;
                case 1:
                    x = screen.WorkingArea.Width - this.Width - 20;
                    y = 10;
                    break;
                case 2:
                    x = 20;
                    y = 10;
                    break;
                case 3:
                    x = (screen.WorkingArea.Width - this.Width) / 2;
                    y = screen.WorkingArea.Height - this.Height - 15;
                    break;
            }
            this.Location = new Point(x, y);
            config.X = x;
            config.Y = y;
            SaveConfig();
        }

        private void ToggleLock()
        {
            config.Locked = !config.Locked;
            SaveConfig();
        }

        private bool IsStartupEnabled()
        {
            try
            {
                using (RegistryKey key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run", false))
                {
                    if (key != null)
                    {
                        return key.GetValue("TopFloatingClock") != null;
                    }
                }
            }
            catch { }
            return false;
        }

        private void ToggleStartup()
        {
            try
            {
                using (RegistryKey key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run", true))
                {
                    if (key != null)
                    {
                        if (IsStartupEnabled())
                        {
                            key.DeleteValue("TopFloatingClock", false);
                        }
                        else
                        {
                            key.SetValue("TopFloatingClock", "\"" + Application.ExecutablePath + "\"");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show("Không thể cấu hình khởi động: " + ex.Message);
            }
        }

        private void LoadConfig()
        {
            config = new Config();
            try
            {
                if (File.Exists(configPath))
                {
                    string json = File.ReadAllText(configPath);
                    if (json.Contains("\"x\":")) config.X = ExtractInt(json, "\"x\":");
                    else if (json.Contains("\"X\":")) config.X = ExtractInt(json, "\"X\":");

                    if (json.Contains("\"y\":")) config.Y = ExtractInt(json, "\"y\":");
                    else if (json.Contains("\"Y\":")) config.Y = ExtractInt(json, "\"Y\":");

                    if (json.Contains("\"opacity\":")) config.Opacity = ExtractDouble(json, "\"opacity\":");
                    else if (json.Contains("\"Opacity\":")) config.Opacity = ExtractDouble(json, "\"Opacity\":");

                    if (json.Contains("\"font_size\":")) config.FontSize = (float)ExtractDouble(json, "\"font_size\":");
                    else if (json.Contains("\"FontSize\":")) config.FontSize = (float)ExtractDouble(json, "\"FontSize\":");

                    if (json.Contains("\"text_color\":")) config.TextColor = ExtractString(json, "\"text_color\":");
                    else if (json.Contains("\"TextColor\":")) config.TextColor = ExtractString(json, "\"TextColor\":");

                    if (json.Contains("\"bg_color\":")) config.BgColor = ExtractString(json, "\"bg_color\":");
                    if (json.Contains("\"locked\":")) config.Locked = json.Contains("\"locked\": true");
                }
            }
            catch { }
        }

        private int ExtractInt(string json, string key)
        {
            int idx = json.IndexOf(key);
            if (idx == -1) return 0;
            int start = idx + key.Length;
            int end = json.IndexOfAny(new char[] { ',', '}', '\r', '\n' }, start);
            string val = json.Substring(start, end - start).Trim();
            int res = 0;
            int.TryParse(val, out res);
            return res;
        }

        private double ExtractDouble(string json, string key)
        {
            int idx = json.IndexOf(key);
            if (idx == -1) return 0;
            int start = idx + key.Length;
            int end = json.IndexOfAny(new char[] { ',', '}', '\r', '\n' }, start);
            string val = json.Substring(start, end - start).Trim();
            double res = 0;
            double.TryParse(val, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out res);
            return res;
        }

        private string ExtractString(string json, string key)
        {
            int idx = json.IndexOf(key);
            if (idx == -1) return "";
            int start = json.IndexOf('"', idx + key.Length) + 1;
            int end = json.IndexOf('"', start);
            return json.Substring(start, end - start);
        }

        private void SaveConfig()
        {
            try
            {
                string json = string.Format(
                    "{{\n  \"x\": {0},\n  \"y\": {1},\n  \"opacity\": {2},\n  \"font_size\": {3},\n  \"text_color\": \"{4}\",\n  \"bg_color\": \"{5}\",\n  \"locked\": {6}\n}}",
                    config.X,
                    config.Y,
                    config.Opacity.ToString(System.Globalization.CultureInfo.InvariantCulture),
                    config.FontSize.ToString(System.Globalization.CultureInfo.InvariantCulture),
                    config.TextColor,
                    config.BgColor,
                    config.Locked ? "true" : "false"
                );
                File.WriteAllText(configPath, json);
            }
            catch { }
        }
    }

    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new FloatingClockForm());
        }
    }
}
