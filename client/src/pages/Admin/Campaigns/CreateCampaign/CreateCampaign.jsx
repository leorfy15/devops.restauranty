import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const url = process.env.REACT_APP_SERVER_URL || window.location.origin;

function CreateCampaign() {
    const [name, setName] = useState("");
    const [start, setStart] = useState("");
    const [end, setEnd] = useState("");
    const [description, setDescription] = useState("");
    const [errorMessage, setErrorMessage] = useState(undefined);

    const navigate = useNavigate();

    const handleName = (e) => setName(e.target.value);
    const handleStart = (e) => setStart(e.target.value);
    const handleEnd = (e) => setEnd(e.target.value);
    const handleDescription = (e) => setDescription(e.target.value);

    const handleSubmit = (e) => {
        e.preventDefault();

        const startDate = new Date(start);
        const endDate = new Date(end);

        // Check if the start date is later than the end date
        if (startDate > endDate) {
            setErrorMessage("The initial date can't be earlier from the expiry date.");
            return;
        }

        // Check if all required fields are filled
        if (!name || !start || !end || !description) {
            setErrorMessage("All fields must be filled.");
            return;
        }

        const requestBody = { name, start, end, description };

        axios
            .post(`${url}/api/discounts/campaign`, requestBody)
            .then((response) => {
                if (response.status === 200) {
                    console.log(response.data);
                    console.log("Coupon Inserted.");
                    navigate("/campaign");
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
                <h1>Create Campaign</h1>
                <div className="inputwrap">
                    <form onSubmit={handleSubmit}>

                        <input className="forms mt-4 m-2" type="text" name="name" value={name} placeholder="Nome da Campanha" onChange={handleName} /><br />

                        <input className="forms m-2" type="text" name="description" placeholder="Descrição da Campanha" value={description} onChange={handleDescription} /><br />

                        <p>Initial Date</p>
                        <input className="forms m-2" type="date" name="start" value={start} onChange={handleStart} /><br />

                        <p>Expiry Date</p>
                        <input className="forms m-2" type="date" name="end" value={end} onChange={handleEnd} /><br />

                        <div>
                            {errorMessage && <p className="error-message">{errorMessage}</p>}
                            <button className="button m-2" type="submit">Create Campaign</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}

export default CreateCampaign;
