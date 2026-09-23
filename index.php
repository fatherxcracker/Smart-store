<?php
$host = "localhost";
$username = "root";  
$password = "";      
$dbname = "smart_store_db";

$message = "";
$message_color = "black";

if ($_SERVER["REQUEST_METHOD"] == "POST") {
    try {
        // Connect to the database using PDO
        $conn = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password);
        $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        // Sanitize and grab the form inputs
        $full_name = trim($_POST['full_name']);
        $address = trim($_POST['address']);
        $telephone_number = trim($_POST['phone']);
        $email_address = trim($_POST['email']);

        // Insert into the customers table
        $sql_customer = "INSERT INTO customers (full_name, address, telephone_number, email_address) 
                         VALUES (:full_name, :address, :telephone_number, :email_address)";
        
        $stmt = $conn->prepare($sql_customer);
        $stmt->execute([
            ':full_name' => $full_name,
            ':address' => $address,
            ':telephone_number' => $telephone_number,
            ':email_address' => $email_address
        ]);

        // Success State: Log hardware trigger (Blue LED = ON)
        $sql_log = "INSERT INTO system_logs (customer_email, status, blue_led, red_led, buzzer, message) 
                    VALUES (:email, 'SUCCESS', 1, 0, 0, 'Customer added successfully. Blue LED activated.')";
        $stmt_log = $conn->prepare($sql_log);
        $stmt_log->execute([':email' => $email_address]);

        // Set frontend success message
        $message = "🎉 Success! Customer data stored and Blue LED turned on.";
        $message_color = "blue";

    } catch (PDOException $e) {
        // Failure State: Log hardware trigger (Red LED & Buzzer = ON)
        try {
            $conn = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password);
            $email_error = isset($_POST['email']) ? trim($_POST['email']) : 'unknown';
            
            $sql_error_log = "INSERT INTO system_logs (customer_email, status, blue_led, red_led, buzzer, message) 
                              VALUES (:email, 'FAILURE', 0, 1, 1, :err_msg)";
            $stmt_error = $conn->prepare($sql_error_log);
            $stmt_error->execute([
                ':email' => $email_error,
                ':err_msg' => "Error: " . $e->getMessage()
            ]);
        } catch (Exception $log_ex) {
            // Fallback if logging fails
        }

        // Set frontend failure message
        $message = "❌ Error! Action failed. Red LED and Buzzer activated. (" . $e->getMessage() . ")";
        $message_color = "red";
    }
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Smart Store</title>
</head>
<body>

<h1>Add Customer</h1>

<!-- Action is empty so it posts back to this same index.php file -->
<form method="POST" action="">

    <label>Name:</label>
    <input type="text" name="full_name" required>
    <br><br>

    <label>Address:</label>
    <input type="text" name="address" required>
    <br><br>

    <label>Telephone:</label>
    <input type="text" name="phone" required>
    <br><br>

    <label>Email:</label>
    <input type="email" name="email" required>
    <br><br>

    <button type="submit">Add Customer</button>

</form>

<!-- Replaced the Jinja syntax with native PHP system notifications -->
<?php if (!empty($message)): ?>
    <p style="color: <?php echo $message_color; ?>; font-weight: bold; font-size: 1.2em;">
        <?php echo $message; ?>
    </p>
<?php endif; ?>

</body>
</html>
