import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const url = process.env.REACT_APP_SERVER_URL || window.location.origin;

function CreateCoupon() {
    const [name, setName] = useState("");
    const [start, setStart] = useState("");
    const [end, setEnd] = useState("");
    const [discount, setDiscount] = useState("");
    const [errorMessage, setErrorMessage] = useState(undefined);

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

        // Check if the start date is later than the end date
        if (startDate > endDate) {
            setErrorMessage("The initial date can't be earlier from the expiry date.");
            return;
        }

        // Check if all required fields are filled
        if (!name || !start || !end || !discount) {
            setErrorMessage("All fields must be filled.");
            return;
        }

        const requestBody = { name, start, end, discount };

        axios
            .post(`${url}/api/discounts/coupons`, requestBody)
            .then((response) => {
                if (response.status === 200) {
                    console.log(response.data);
                    console.log("Coupon Inserted.");
                    navigate("/discounts/coupons");
                }
            })
            .catch((error) => {
                console.error(error);
                const errorDescription = error.response.data.message;
                setErrorMessage(errorDescription);
            });
    };

    return (
        <div className="main">
            <div>
                <h1>Create Coupon</h1>
                <div className="inputwrap">
                    <form onSubmit={ItemhandleSubmit}>
                        <input className="forms mt-4 m-2" type="text" name="name" value={name} placeholder="Code do Coupon" onChange={handleName} /><br />

                        <input className="forms m-2" type="text" name="discount" value={discount} placeholder="Valor do Desconto(%)" onChange={handleDiscount} /><br />

                        <p>Data Inicial</p>
                        <input className="forms m-2" type="date" name="start" value={start} onChange={handleStart} />

                        <p>Data de Expiração</p>
                        <input className="forms m-2" type="date" name="end" value={end} onChange={handleEnd} />
                        <div>
                            {errorMessage && <p className="error-message">{errorMessage}</p>}
                            <button className="button m-2" type="submit">Create Coupon</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

export default CreateCoupon;
