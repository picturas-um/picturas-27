const amqp = require('amqplib/callback_api');

const rabbit_host = process.env.RABBITMQ_HOST;
const rabbit_port = process.env.RABBITMQ_PORT;
const rabbit_username = process.env.RABBITMQ_USER;
const rabbit_password = process.env.RABBITMQ_PASS;
const exchange = "picturas";

const rabbit_mq_sv = `amqp://${rabbit_username}:${rabbit_password}@${rabbit_host}:${rabbit_port}`;

function send_rabbit_msg(msg, queue) {
    amqp.connect(rabbit_mq_sv, (err_sv, connection) => {
        if (err_sv) throw err_sv;
        
        connection.createChannel( (err_conn, channel) => {
            if (err_conn) throw err_conn;
            
            channel.assertExchange(exchange, 'direct', {
                durable: true
            });

            channel.publish(exchange, queue, Buffer.from(JSON.stringify(msg)));
        });
        
        setTimeout(() => {
            connection.close();
        }, 500);
    });
    
}

// Consumes `queue` and reconnects automatically if the broker connection drops
// (e.g. RabbitMQ restarts). Without this, the gateway kept running but stopped
// consuming ws_queue, so no progress or preview events reached the clients.
function read_rabbit_msg(queue, callback) {
    const RETRY_MS = 3000;

    const retry = (reason) => {
        console.error(`[rabbit] ${reason}; reconnecting in ${RETRY_MS / 1000}s`);
        setTimeout(() => read_rabbit_msg(queue, callback), RETRY_MS);
    };

    amqp.connect(rabbit_mq_sv, (err_sv, connection) => {
        if (err_sv) return retry(`connection failed: ${err_sv.message}`);

        let closed = false;
        const onDown = (reason) => {
            if (closed) return;
            closed = true;
            retry(reason);
        };
        connection.on('error', (err) => console.error('[rabbit] connection error:', err.message));
        connection.on('close', () => onDown('connection closed'));

        connection.createChannel((err_conn, channel) => {
            if (err_conn) {
                connection.close();
                return onDown(`channel failed: ${err_conn.message}`);
            }

            channel.assertExchange(exchange, 'direct', {
                durable: true
              });

            channel.assertQueue(queue, { durable: true }, (err_queue, q) => {
                if (err_queue) {
                    connection.close();
                    return onDown(`queue failed: ${err_queue.message}`);
                }

                console.log(`[rabbit] consuming ${q.queue}`);
                channel.consume(q.queue, (msg) => {
                    if(msg != null){
                        try {
                            callback(msg);
                        } catch (e) {
                            console.error('[rabbit] error handling message:', e);
                        }
                        // Acknowledge the message
                        channel.ack(msg);
                    }
                }, {
                    noAck: false
                });
            });
        });
    });
}

module.exports = { send_rabbit_msg, read_rabbit_msg };
