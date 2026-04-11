using System.Data;
using Microsoft.Data.Sqlite;
using System.Windows.Forms;

namespace HaewadalMotel;

internal static class Program
{
    [STAThread]
    static void Main()
    {
        ApplicationConfiguration.Initialize();
        var dbPath = Path.Combine(AppContext.BaseDirectory, "motel_native.db");
        var repository = new MotelRepository(dbPath);
        Application.Run(new MainForm(repository));
    }
}

public sealed class MainForm : Form
{
    private readonly MotelRepository _repository;
    private readonly DataGridView _grid;
    private readonly Label _stats;

    public MainForm(MotelRepository repository)
    {
        _repository = repository;
        Text = "해와달 모텔 관리 시스템 (Python 없이 실행)";
        Width = 1100;
        Height = 700;

        var topPanel = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 52, Padding = new Padding(10) };
        var refreshButton = new Button { Text = "새로고침", Width = 100 };
        var checkinButton = new Button { Text = "체크인", Width = 100 };
        var checkoutButton = new Button { Text = "체크아웃", Width = 100 };
        var cleaningButton = new Button { Text = "청소중", Width = 100 };
        var availableButton = new Button { Text = "이용가능", Width = 100 };

        refreshButton.Click += (_, _) => RefreshData();
        checkinButton.Click += (_, _) => CheckInSelectedRoom();
        checkoutButton.Click += (_, _) => ChangeSelectedRoom(RoomStatus.Available, checkout: true);
        cleaningButton.Click += (_, _) => ChangeSelectedRoom(RoomStatus.Cleaning, checkout: false);
        availableButton.Click += (_, _) => ChangeSelectedRoom(RoomStatus.Available, checkout: false);

        topPanel.Controls.Add(refreshButton);
        topPanel.Controls.Add(checkinButton);
        topPanel.Controls.Add(checkoutButton);
        topPanel.Controls.Add(cleaningButton);
        topPanel.Controls.Add(availableButton);

        _stats = new Label { Dock = DockStyle.Top, Height = 28, TextAlign = ContentAlignment.MiddleLeft, Padding = new Padding(12, 0, 0, 0) };

        _grid = new DataGridView
        {
            Dock = DockStyle.Fill,
            ReadOnly = true,
            AutoGenerateColumns = true,
            SelectionMode = DataGridViewSelectionMode.FullRowSelect,
            MultiSelect = false,
            AllowUserToAddRows = false,
            AllowUserToDeleteRows = false
        };

        Controls.Add(_grid);
        Controls.Add(_stats);
        Controls.Add(topPanel);

        RefreshData();
    }

    private string? SelectedRoomNumber()
    {
        if (_grid.CurrentRow?.DataBoundItem is not DataRowView row) return null;
        return row["room_number"]?.ToString();
    }

    private void RefreshData()
    {
        _grid.DataSource = _repository.ListRooms();
        var stats = _repository.GetStats();
        _stats.Text = $"이용가능 {stats.Available} | 사용중 {stats.Occupied} | 청소중 {stats.Cleaning} | 오늘 매출 {stats.TodayRevenue:N0}원";
    }

    private void CheckInSelectedRoom()
    {
        var roomNo = SelectedRoomNumber();
        if (string.IsNullOrWhiteSpace(roomNo))
        {
            MessageBox.Show("객실을 먼저 선택해주세요.");
            return;
        }

        var name = Prompt.Show("고객명", "체크인");
        if (string.IsNullOrWhiteSpace(name)) return;

        var phone = Prompt.Show("전화번호", "체크인") ?? string.Empty;
        var checkout = Prompt.Show("예상 체크아웃 (예: 2026-01-01 12:00)", "체크인") ?? string.Empty;
        var priceInput = Prompt.Show("요금(숫자)", "체크인") ?? "0";
        if (!int.TryParse(priceInput, out var price) || price < 0)
        {
            MessageBox.Show("요금은 0 이상의 숫자로 입력해주세요.");
            return;
        }

        _repository.CheckIn(roomNo, name, phone, checkout, price);
        RefreshData();
    }

    private void ChangeSelectedRoom(RoomStatus status, bool checkout)
    {
        var roomNo = SelectedRoomNumber();
        if (string.IsNullOrWhiteSpace(roomNo))
        {
            MessageBox.Show("객실을 먼저 선택해주세요.");
            return;
        }

        if (checkout)
            _repository.CheckOut(roomNo);
        else
            _repository.UpdateStatus(roomNo, status);

        RefreshData();
    }
}

public enum RoomStatus
{
    Available,
    Occupied,
    Cleaning
}

public sealed class MotelRepository
{
    private readonly string _connectionString;

    public MotelRepository(string dbPath)
    {
        _connectionString = new SqliteConnectionStringBuilder { DataSource = dbPath }.ToString();
        Init();
        SeedIfEmpty();
    }

    private void Init()
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();
        var cmd = conn.CreateCommand();
        cmd.CommandText = @"
CREATE TABLE IF NOT EXISTS rooms (
  room_number TEXT PRIMARY KEY,
  room_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'available',
  guest_name TEXT,
  guest_phone TEXT,
  checkin_at TEXT,
  checkout_at TEXT,
  price INTEGER DEFAULT 0,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stay_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room_number TEXT NOT NULL,
  guest_name TEXT NOT NULL,
  guest_phone TEXT,
  checkin_at TEXT NOT NULL,
  checkout_at TEXT NOT NULL,
  final_price INTEGER NOT NULL,
  created_at TEXT NOT NULL
);";
        cmd.ExecuteNonQuery();
    }

    private void SeedIfEmpty()
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();
        using var countCmd = conn.CreateCommand();
        countCmd.CommandText = "SELECT COUNT(*) FROM rooms";
        var count = Convert.ToInt32(countCmd.ExecuteScalar());
        if (count > 0) return;

        var types = new[] { "standard", "ondol", "twin", "couple", "longterm" };
        var now = DateTime.Now.ToString("s");
        for (var floor = 1; floor <= 3; floor++)
        {
            for (var i = 1; i <= 10; i++)
            {
                var roomNo = $"{floor}{i:00}";
                using var cmd = conn.CreateCommand();
                cmd.CommandText = "INSERT INTO rooms (room_number, room_type, status, updated_at) VALUES ($n,$t,'available',$u)";
                cmd.Parameters.AddWithValue("$n", roomNo);
                cmd.Parameters.AddWithValue("$t", types[(i - 1) % types.Length]);
                cmd.Parameters.AddWithValue("$u", now);
                cmd.ExecuteNonQuery();
            }
        }
    }

    public DataTable ListRooms()
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = @"
SELECT room_number, room_type, status,
       COALESCE(guest_name, '') AS guest_name,
       COALESCE(guest_phone, '') AS guest_phone,
       COALESCE(checkin_at, '') AS checkin_at,
       COALESCE(checkout_at, '') AS checkout_at,
       COALESCE(price, 0) AS price
FROM rooms ORDER BY room_number";

        using var reader = cmd.ExecuteReader();
        var table = new DataTable();
        table.Load(reader);
        return table;
    }

    public void CheckIn(string roomNo, string name, string phone, string expectedCheckout, int price)
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = @"
UPDATE rooms
SET status='occupied', guest_name=$name, guest_phone=$phone,
    checkin_at=$checkin, checkout_at=$checkout, price=$price, updated_at=$updated
WHERE room_number=$room";
        var now = DateTime.Now.ToString("s");
        cmd.Parameters.AddWithValue("$name", name);
        cmd.Parameters.AddWithValue("$phone", phone);
        cmd.Parameters.AddWithValue("$checkin", now);
        cmd.Parameters.AddWithValue("$checkout", expectedCheckout);
        cmd.Parameters.AddWithValue("$price", price);
        cmd.Parameters.AddWithValue("$updated", now);
        cmd.Parameters.AddWithValue("$room", roomNo);
        cmd.ExecuteNonQuery();
    }

    public void CheckOut(string roomNo)
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();

        string guestName = "-";
        string guestPhone = "";
        string checkin = DateTime.Now.ToString("s");
        int price = 0;

        using (var roomCmd = conn.CreateCommand())
        {
            roomCmd.CommandText = "SELECT guest_name, guest_phone, checkin_at, price, status FROM rooms WHERE room_number=$room";
            roomCmd.Parameters.AddWithValue("$room", roomNo);
            using var reader = roomCmd.ExecuteReader();
            if (!reader.Read() || reader.GetString(4) != "occupied") return;
            guestName = reader.IsDBNull(0) ? "-" : reader.GetString(0);
            guestPhone = reader.IsDBNull(1) ? "" : reader.GetString(1);
            checkin = reader.IsDBNull(2) ? checkin : reader.GetString(2);
            price = reader.IsDBNull(3) ? 0 : reader.GetInt32(3);
        }

        var now = DateTime.Now.ToString("s");
        using (var historyCmd = conn.CreateCommand())
        {
            historyCmd.CommandText = @"
INSERT INTO stay_history (room_number, guest_name, guest_phone, checkin_at, checkout_at, final_price, created_at)
VALUES ($room,$name,$phone,$checkin,$checkout,$price,$created)";
            historyCmd.Parameters.AddWithValue("$room", roomNo);
            historyCmd.Parameters.AddWithValue("$name", guestName);
            historyCmd.Parameters.AddWithValue("$phone", guestPhone);
            historyCmd.Parameters.AddWithValue("$checkin", checkin);
            historyCmd.Parameters.AddWithValue("$checkout", now);
            historyCmd.Parameters.AddWithValue("$price", price);
            historyCmd.Parameters.AddWithValue("$created", now);
            historyCmd.ExecuteNonQuery();
        }

        using var updateCmd = conn.CreateCommand();
        updateCmd.CommandText = @"
UPDATE rooms SET status='available', guest_name=NULL, guest_phone=NULL, checkin_at=NULL,
                 checkout_at=NULL, price=0, updated_at=$updated
WHERE room_number=$room";
        updateCmd.Parameters.AddWithValue("$updated", now);
        updateCmd.Parameters.AddWithValue("$room", roomNo);
        updateCmd.ExecuteNonQuery();
    }

    public void UpdateStatus(string roomNo, RoomStatus status)
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "UPDATE rooms SET status=$status, updated_at=$updated WHERE room_number=$room";
        cmd.Parameters.AddWithValue("$status", status.ToString().ToLowerInvariant());
        cmd.Parameters.AddWithValue("$updated", DateTime.Now.ToString("s"));
        cmd.Parameters.AddWithValue("$room", roomNo);
        cmd.ExecuteNonQuery();
    }

    public (int Available, int Occupied, int Cleaning, int TodayRevenue) GetStats()
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();

        int CountBy(string value)
        {
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT COUNT(*) FROM rooms WHERE status=$status";
            cmd.Parameters.AddWithValue("$status", value);
            return Convert.ToInt32(cmd.ExecuteScalar());
        }

        using var revenueCmd = conn.CreateCommand();
        revenueCmd.CommandText = "SELECT COALESCE(SUM(final_price),0) FROM stay_history WHERE substr(checkout_at,1,10)=$today";
        revenueCmd.Parameters.AddWithValue("$today", DateTime.Today.ToString("yyyy-MM-dd"));
        var todayRevenue = Convert.ToInt32(revenueCmd.ExecuteScalar());

        return (CountBy("available"), CountBy("occupied"), CountBy("cleaning"), todayRevenue);
    }
}

public static class Prompt
{
    public static string? Show(string text, string caption)
    {
        using var form = new Form
        {
            Width = 420,
            Height = 170,
            Text = caption,
            FormBorderStyle = FormBorderStyle.FixedDialog,
            StartPosition = FormStartPosition.CenterParent,
            MinimizeBox = false,
            MaximizeBox = false
        };

        var label = new Label { Left = 16, Top = 16, Text = text, Width = 370 };
        var input = new TextBox { Left = 16, Top = 42, Width = 370 };
        var ok = new Button { Text = "확인", Left = 226, Width = 75, Top = 76, DialogResult = DialogResult.OK };
        var cancel = new Button { Text = "취소", Left = 311, Width = 75, Top = 76, DialogResult = DialogResult.Cancel };

        form.Controls.Add(label);
        form.Controls.Add(input);
        form.Controls.Add(ok);
        form.Controls.Add(cancel);
        form.AcceptButton = ok;
        form.CancelButton = cancel;

        return form.ShowDialog() == DialogResult.OK ? input.Text : null;
    }
}
