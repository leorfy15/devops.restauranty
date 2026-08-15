import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";

const url = process.env.REACT_APP_SERVER_URL || window.location.origin;

function EditCoupon() {
    const [coupon, setCoupon] = useState("");
    const [name, setName] = useState("");
    const [start, setStart] = useState("");
    const [end, setEnd] = useState("");
    const [discount, setDiscount] = useState("");
    const [errorMessage, setErrorMessage] = useState(undefined);
    const { CouponId } = useParams();

    useEffect(() => {
        axios.get(`${url}/api/discounts/coupons/${CouponId}`).then((response) => {
            setCoupon(response.data);
            setName(response.data.name)
            setDiscount(response.data.discount)
            setStart(response.data.start)
            setEnd(response.data.end)
            console.log(response.data);
        });
    }, []);



    const navigate = useNavigate();

    const handleName = (e) => setName(e.target.value);
    const handleStart = (e) => setStart(e.target.value);
    const handleEnd = (e) => setEnd(e.target.value);
    const handleDiscount = (e) => {
        const inputDiscount = e.target.value;
        // Remove non-digit characters from the input
        const sanitizedDiscount = inputDiscount.replace(/\D/g, "");
        setDiscount(sanitizedDiscount);
    };

    const ItemhandleSubmit = (e) => {
        e.preventDefault();

        const startDate = new Date(start);
        const endDate = new Date(end);
        if (!name || !start || !end || !discount) {
            setErrorMessage("All fields must be filled.");
            return;
        }

        // Check if the start date is later than the end date
        if (startDate > endDate) {
            setErrorMessage("The initial date mustn't be before the expiry date.");
            return;
        }

        let _id = coupon._id;
        const requestBody = { _id, name, start, end, discount };

        axios
            .put(`${url}/api/discounts/coupons/${coupon._id}`, requestBody)
            .then((response) => {
                if (response.status === 200) {
                    console.log(response.data);
                }
                navigate("/discounts/coupons");
            })
            .catch((error) => {
                console.error(error);
                const errorDescription = error.response.data.message;
                setErrorMessage(errorDescription);
            });
    };

    return (
        <div className="main">
            <div className="max-w-[400px]">
                <h1>Edit Coupon {coupon.name} </h1>
                <div className="inputwrap">
                    <form onSubmit={ItemhandleSubmit}>
                        <input className="forms mt-4 m-2" type="text" name="name" value={name} onChange={handleName} placeholder="Code Coupon" /><br />

                        <input className="forms m-2" type="text" name="discount" value={discount} onChange={handleDiscount} placeholder="Discount Amount(%)" /><br />

                        <p>Starting Date:</p>
                        <input className="forms m-2" type="date" name="start" value={start} onChange={handleStart} />

                        <p>Expiration Date:</p>
                        <input className="forms m-2" type="date" name="end" value={end} onChange={handleEnd} />
                        <div>
                            {errorMessage && <p className="error-message">{errorMessage}</p>}
                            <button className="button m-2" type="submit">Edit Item</button>
                            <Link to={`/discounts/coupons`}><button className="button cancel m-2">Cancel</button></Link>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

export default EditCoupon;
